"""Extract structured delivery info from each WhatsApp message using Claude.

Standard library only. The model never does date arithmetic: it says *which* date the message
refers to ("kal", "Monday", "23rd"), and resolve_date() turns that into a calendar date.

Usage:
    python3 extract.py --ids m02,m29      # specific messages
    python3 extract.py --all              # everything
    python3 extract.py --ids m02 --force  # ignore cache
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
MESSAGES_FILE = ROOT / "data" / "messages.json"
OUT_FILE = ROOT / "out" / "extractions.json"

MODEL = os.environ.get("KAJ_MODEL", "claude-haiku-5-5")
PROMPT_VERSION = "v2"
API_URL = "https://api.anthropic.com/v1/messages"

MSG_TYPES = ["promise", "dispatch", "delivered_claim", "excuse", "query", "other"]
MATERIALS = ["steel", "cement", "sand", "aggregate", "rmc", "aac_blocks", "electrical", "unknown"]
DATE_REFS = ["today", "tomorrow", "day_after", "weekday", "day_of_month", "vague", "none"]
DIRECTIONS = ["future", "past", "none"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

TOOL = {
    "name": "record_extraction",
    "description": "Record the structured reading of one supplier/site WhatsApp message.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["msg_type", "material", "date_expr", "date_ref", "weekday", "day_of_month",
                     "date_direction", "commitment_level", "evidence", "reason"],
        "properties": {
            "msg_type": {"type": "string", "enum": MSG_TYPES},
            "material": {"type": "string", "enum": MATERIALS},
            "date_expr": {"type": ["string", "null"], "description": "Exact words in the message that give the delivery date, e.g. 'kal', 'parso morning', 'by 23rd'. null if none."},
            "date_ref": {"type": "string", "enum": DATE_REFS},
            "weekday": {"type": ["string", "null"], "enum": WEEKDAYS + [None]},
            "day_of_month": {"type": ["integer", "null"], "minimum": 1, "maximum": 31},
            "date_direction": {"type": "string", "enum": DIRECTIONS},
            "commitment_level": {"type": "integer", "enum": [0, 1, 2, 3]},
            "evidence": {"type": "array", "items": {"type": "string"}, "description": "Verifiable dispatch proof quoted from the message: vehicle no., LR/challan no., driver name/phone. Empty if none."},
            "reason": {"type": "string", "description": "One short sentence a site manager could read."},
        },
    },
}

SYSTEM = """You read WhatsApp messages between Indian construction suppliers and site engineers.
Messages are in English, Hinglish or Bengali-English. Record each one with the record_extraction tool.

Rules:
- msg_type: promise (a future delivery), dispatch (says goods have left), delivered_claim (says goods arrived),
  excuse (reason for delay with no new date), query (asking for status), other.
  An excuse that also gives a new date is a promise.
- material: only what the message itself names. Translations: baali/balu = sand; stone chips/gitti = aggregate;
  TMT/sariya/rod = steel; blocks = aac_blocks; cable/conduit/wire = electrical. If not named, use unknown,
  even if the previous messages make it obvious.
- Dates are about when the material reaches the site, not when it is loaded.
- "kal" (Hindi) and "kal"/"kalke" (Bengali) mean tomorrow OR yesterday. Decide from the verb tense:
  "aa jayega / bhejenge / pathabo" = future; "aa gaya / pahunch gaya / gechhe / chhilo" = past.
  date_direction is the direction of the delivery date, not of other events in the message.
- date_ref: today (aaj, "by evening"), tomorrow (kal/kalke, future), day_after (parso/porshu),
  weekday (set weekday), day_of_month (set day_of_month, e.g. "by 23rd"), vague ("jaldi", "2-3 din", "this week"),
  none (no date). For past dates use the same refs (kal past = tomorrow + direction past).
- commitment_level: 0 = excuse or no commitment; 1 = vague promise, no specific day; 2 = specific day promised,
  including "truck nikal gaya" with no proof; 3 = dispatch with verifiable evidence
  (vehicle number, LR/challan number, driver name or phone).
  If the message gives a specific delivery day (aaj, kal, parso, a weekday, a date) in the future, the level is
  at least 2, even if the message also gives an excuse. "pakka", "confirm", "100%" neither raise nor lower the level.
  Site-engineer messages are 0.
"""


# ---------- validation ----------

def validate(x: dict) -> list[str]:
    """Return a list of problems. Empty list means valid."""
    errors = []
    required = TOOL["input_schema"]["required"]
    for key in required:
        if key not in x:
            errors.append(f"missing field: {key}")
    extra = set(x) - set(required)
    if extra:
        errors.append(f"unexpected fields: {sorted(extra)}")
    if errors:
        return errors

    def check_enum(field, allowed):
        if x[field] not in allowed:
            errors.append(f"{field}={x[field]!r} not in {allowed}")

    check_enum("msg_type", MSG_TYPES)
    check_enum("material", MATERIALS)
    check_enum("date_ref", DATE_REFS)
    check_enum("date_direction", DIRECTIONS)
    check_enum("commitment_level", [0, 1, 2, 3])
    check_enum("weekday", WEEKDAYS + [None])
    if x["day_of_month"] is not None and not (isinstance(x["day_of_month"], int) and 1 <= x["day_of_month"] <= 31):
        errors.append(f"day_of_month={x['day_of_month']!r} must be 1-31 or null")
    if not isinstance(x["evidence"], list) or not all(isinstance(e, str) for e in x["evidence"]):
        errors.append("evidence must be a list of strings")
    if errors:
        return errors

    # Consistency rules between fields
    if (x["date_ref"] == "weekday") != (x["weekday"] is not None):
        errors.append("weekday must be set exactly when date_ref is 'weekday'")
    if (x["date_ref"] == "day_of_month") != (x["day_of_month"] is not None):
        errors.append("day_of_month must be set exactly when date_ref is 'day_of_month'")
    if x["date_ref"] == "none" and x["date_direction"] != "none":
        errors.append("date_ref 'none' needs date_direction 'none'")
    if x["date_ref"] != "none" and x["date_direction"] == "none":
        errors.append("a date_ref other than 'none' needs date_direction future or past")
    if x["commitment_level"] == 3 and not x["evidence"]:
        errors.append("commitment_level 3 requires at least one evidence item")
    if x["commitment_level"] == 2 and x["date_ref"] in ("vague", "none"):
        errors.append("commitment_level 2 needs a specific day (date_ref not vague/none)")
    if x["commitment_level"] in (0, 1) and x["date_direction"] == "future" \
            and x["date_ref"] in ("today", "tomorrow", "day_after", "weekday", "day_of_month"):
        errors.append("a specific future delivery day means commitment_level must be at least 2")
    return errors


# ---------- date resolution (deterministic, no model) ----------

def resolve_date(x: dict, sent_on: date) -> date | None:
    """Promised delivery date for future-looking messages. None if there is no specific day."""
    if x["date_direction"] != "future":
        return None
    ref = x["date_ref"]
    if ref == "today":
        return sent_on
    if ref == "tomorrow":
        return sent_on + timedelta(days=1)
    if ref == "day_after":
        return sent_on + timedelta(days=2)
    if ref == "weekday":
        # Next occurrence. Same weekday as today means next week.
        ahead = (WEEKDAYS.index(x["weekday"]) - sent_on.weekday()) % 7 or 7
        return sent_on + timedelta(days=ahead)
    if ref == "day_of_month":
        # First month (this one or later) where that day exists and hasn't passed.
        d = x["day_of_month"]
        y, m = sent_on.year, sent_on.month
        for _ in range(3):
            try:
                candidate = date(y, m, d)
                if candidate >= sent_on:
                    return candidate
            except ValueError:
                pass
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        return None
    return None


# ---------- API ----------

def call_claude(messages: list[dict]) -> dict:
    """One API call with the tool forced. Retries transient errors. Raises RuntimeError on failure."""
    body = json.dumps({
        "model": MODEL,
        "max_tokens": 600,
        "system": SYSTEM,
        "tools": [TOOL],
        "tool_choice": {"type": "tool", "name": TOOL["name"]},
        "messages": messages,
    }).encode()
    headers = {
        "content-type": "application/json",
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
        "anthropic-version": "2023-06-01",
    }
    last_error = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(API_URL, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}"
            if e.code not in (429, 500, 502, 503, 529):
                break  # bad request / auth: retrying won't help
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_error = f"network: {e}"
        time.sleep(2 ** attempt)
    raise RuntimeError(last_error)


def build_prompt(msg: dict, history: list[dict]) -> str:
    sent = date.fromisoformat(msg["sent_at"][:10])
    lines = [f"Chat: {msg['chat']}", f"Sent: {msg['sent_at']} ({WEEKDAYS[sent.weekday()]})", ""]
    if history:
        lines.append("Previous messages in this chat (context only):")
        lines += [f"  [{h['sent_at'][:16]}] {h['sender_role']}: {h['text']}" for h in history]
        lines.append("")
    lines.append(f"Message to record ({msg['sender_role']}): {msg['text']}")
    return "\n".join(lines)


def extract_one(msg: dict, history: list[dict]) -> dict:
    """Never raises. Returns a record with status ok / retried / needs_review."""
    convo = [{"role": "user", "content": build_prompt(msg, history)}]
    record = {"id": msg["id"], "model": MODEL, "prompt_version": PROMPT_VERSION}
    errors: list[str] = []
    first_errors = None  # validation errors from attempt 1, kept for the eval
    for attempt in range(2):  # first try + one retry with the validation errors
        try:
            resp = call_claude(convo)
        except Exception as e:  # network/auth/anything: flag, don't crash
            return {**record, "status": "needs_review", "error": f"api: {e}",
                    "first_attempt_errors": first_errors, "extraction": None}
        tool_use = next((b for b in resp.get("content", []) if b.get("type") == "tool_use"), None)
        if tool_use is None:
            errors = ["no tool_use block in response"]
            if attempt == 0:
                first_errors = errors
            continue
        x = tool_use["input"]
        errors = validate(x)
        if not errors:
            promised = resolve_date(x, date.fromisoformat(msg["sent_at"][:10]))
            return {**record, "status": "ok" if attempt == 0 else "retried", "error": None,
                    "first_attempt_errors": first_errors,
                    "extraction": x, "promised_date": promised.isoformat() if promised else None}
        if attempt == 0:
            first_errors = errors
        # Feed the problems back and ask again
        convo += [
            {"role": "assistant", "content": resp["content"]},
            {"role": "user", "content": [{
                "type": "tool_result", "tool_use_id": tool_use["id"], "is_error": True,
                "content": "Invalid: " + "; ".join(errors) + ". Call record_extraction again with these fixed.",
            }]},
        ]
    return {**record, "status": "needs_review", "error": "; ".join(errors),
            "first_attempt_errors": first_errors, "extraction": None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", help="comma-separated message ids")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true", help="re-extract even if cached")
    args = ap.parse_args()
    if not args.ids and not args.all:
        ap.error("give --ids or --all")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set")

    msgs = json.loads(MESSAGES_FILE.read_text())
    wanted = {m["id"] for m in msgs} if args.all else set(args.ids.split(","))
    unknown = wanted - {m["id"] for m in msgs}
    if unknown:
        sys.exit(f"unknown ids: {sorted(unknown)}")

    OUT_FILE.parent.mkdir(exist_ok=True)
    cache = json.loads(OUT_FILE.read_text()) if OUT_FILE.exists() else {}

    for i, msg in enumerate(msgs):
        if msg["id"] not in wanted:
            continue
        cached = cache.get(msg["id"])
        if cached and not args.force and cached.get("prompt_version") == PROMPT_VERSION and cached["status"] != "needs_review":
            print(f"{msg['id']}: cached")
            continue
        history = [m for m in msgs[:i] if m["chat"] == msg["chat"]][-3:]
        rec = extract_one(msg, history)
        cache[msg["id"]] = rec
        OUT_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False))  # save as we go
        x = rec["extraction"] or {}
        print(f"{msg['id']}: {rec['status']:<12} {x.get('msg_type', '-'):<15} {x.get('material', '-'):<10} "
              f"level={x.get('commitment_level', '-')} promised={rec.get('promised_date')} {rec['error'] or ''}")
        if rec.get("first_attempt_errors"):
            print(f"      first attempt: {'; '.join(rec['first_attempt_errors'])}")


if __name__ == "__main__":
    main()
