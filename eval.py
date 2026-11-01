"""Compare extractions against the labelled 15 (data/gold_15_labelled.csv).

Usage:
    python3 eval.py --tag before          # score, print failures, save out/eval_before.json
    python3 eval.py --tag after --compare before
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
LABELS = ROOT / "data" / "gold_15_labelled.csv"
EXTRACTIONS = ROOT / "out" / "extractions.json"

FIELDS = ["msg_type", "material", "date_direction", "promised_date", "commitment_level"]


def predicted(rec: dict) -> dict:
    if not rec or rec["status"] == "needs_review":
        return {f: "NEEDS_REVIEW" for f in FIELDS}
    x = rec["extraction"]
    return {
        "msg_type": x["msg_type"],
        "material": x["material"],
        "date_direction": x["date_direction"],
        "promised_date": rec["promised_date"] or "",
        "commitment_level": str(x["commitment_level"]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--compare", help="tag of an earlier run to compare against")
    args = ap.parse_args()

    if not LABELS.exists():
        sys.exit(f"No labels yet: expected {LABELS}")
    gold = {r["id"]: r for r in csv.DictReader(open(LABELS, encoding="utf-8"))}
    preds = json.loads(EXTRACTIONS.read_text())

    missing = [i for i in gold if i not in preds]
    if missing:
        sys.exit(f"Not extracted yet: {missing}")

    rows = []
    for i, g in gold.items():
        p = predicted(preds[i])
        for f in FIELDS:
            want = (g[f] or "").strip()
            rows.append({"id": i, "field": f, "gold": want, "pred": p[f], "ok": want == p[f],
                         "text": g["text"], "notes": g.get("notes", "")})

    print(f"Accuracy on {len(gold)} labelled messages ({args.tag}):")
    summary = {}
    for f in FIELDS:
        ok = sum(r["ok"] for r in rows if r["field"] == f)
        summary[f] = ok
        print(f"  {f:<17} {ok:>2}/{len(gold)}")
    all_ok = sum(all(r["ok"] for r in rows if r["id"] == i) for i in gold)
    print(f"  {'all fields right':<17} {all_ok:>2}/{len(gold)}")

    print("\nFailures:")
    for r in rows:
        if not r["ok"]:
            reason = (preds[r["id"]].get("extraction") or {}).get("reason", preds[r["id"]].get("error"))
            print(f"  {r['id']} {r['field']:<17} gold={r['gold']!r:<14} pred={r['pred']!r:<14} | {r['text']}")
            print(f"      model said: {reason}" + (f" | your note: {r['notes']}" if r["notes"] else ""))

    # Retries: how often the first answer failed validation, and why
    statuses = {"ok": 0, "retried": 0, "needs_review": 0}
    first_errors = {}
    for i in gold:
        rec = preds[i]
        statuses[rec["status"]] = statuses.get(rec["status"], 0) + 1
        if rec.get("first_attempt_errors"):
            first_errors[i] = rec["first_attempt_errors"]
    print(f"\nStatus: ok {statuses['ok']} | retried {statuses['retried']} | needs_review {statuses['needs_review']}")
    if first_errors:
        print("First-attempt validation errors:")
        for i, errs in first_errors.items():
            print(f"  {i}: {'; '.join(errs)}")
    missing_log = [i for i in gold if preds[i]["status"] != "ok" and "first_attempt_errors" not in preds[i]]
    if missing_log:
        print(f"  (no first-attempt log for {missing_log}: extracted before logging was added)")

    out = ROOT / "out" / f"eval_{args.tag}.json"
    out.write_text(json.dumps({"summary": summary, "all_ok": all_ok, "statuses": statuses,
                               "first_attempt_errors": first_errors, "rows": rows}, indent=2, ensure_ascii=False))

    if args.compare:
        prev = json.loads((ROOT / "out" / f"eval_{args.compare}.json").read_text())
        print(f"\n{args.compare} -> {args.tag}:")
        for f in FIELDS:
            print(f"  {f:<17} {prev['summary'][f]:>2} -> {summary[f]:>2}")
        print(f"  {'all fields right':<17} {prev['all_ok']:>2} -> {all_ok:>2}")
        prev_status = prev.get("statuses", {})
        for s in ("ok", "retried", "needs_review"):
            print(f"  {'status ' + s:<17} {prev_status.get(s, '?'):>2} -> {statuses[s]:>2}")
        before = {(r["id"], r["field"]): r["ok"] for r in prev["rows"]}
        for r in rows:
            was = before.get((r["id"], r["field"]))
            if was is not None and was != r["ok"]:
                print(f"  {'FIXED' if r['ok'] else 'BROKE'}: {r['id']} {r['field']}")


if __name__ == "__main__":
    main()
