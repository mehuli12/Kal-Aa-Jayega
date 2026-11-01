"""Diagnostic only: one attempt per message, no retry, nothing saved.
Prints the raw first answer and the validation errors.

    python3 debug_first_attempt.py m02 m29
"""
import json
import sys

from extract import MESSAGES_FILE, TOOL, build_prompt, call_claude, validate

msgs = json.loads(MESSAGES_FILE.read_text())
for wanted in sys.argv[1:]:
    i = next(n for n, m in enumerate(msgs) if m["id"] == wanted)
    msg = msgs[i]
    history = [m for m in msgs[:i] if m["chat"] == msg["chat"]][-3:]
    resp = call_claude([{"role": "user", "content": build_prompt(msg, history)}])
    print(f"===== {wanted}: {msg['text']}")
    print("stop_reason:", resp.get("stop_reason"))
    tool_use = next((b for b in resp.get("content", []) if b.get("type") == "tool_use"), None)
    if tool_use is None:
        print("NO tool_use block. Raw content:")
        print(json.dumps(resp.get("content"), indent=1, ensure_ascii=False))
        continue
    print("raw first answer:")
    print(json.dumps(tool_use["input"], indent=1, ensure_ascii=False))
    errors = validate(tool_use["input"])
    print("validation:", "PASSED" if not errors else "FAILED")
    for e in errors:
        print("  -", e)
