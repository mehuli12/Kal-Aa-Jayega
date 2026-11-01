"""Count raw field changes between two extraction snapshots, on the labelled 15.

    python3 compare_runs.py out/extractions_before.json out/extractions_noise.json
"""
import csv
import json
import sys

FIELDS = ["msg_type", "material", "date_direction", "commitment_level", "promised_date", "status"]

a, b = (json.load(open(p)) for p in sys.argv[1:3])
ids = [r["id"] for r in csv.DictReader(open("data/gold_15_labelled.csv", encoding="utf-8"))]


def values(rec):
    x = rec.get("extraction") or {}
    return {"msg_type": x.get("msg_type"), "material": x.get("material"),
            "date_direction": x.get("date_direction"), "commitment_level": x.get("commitment_level"),
            "promised_date": rec.get("promised_date"), "status": rec["status"]}


flips = 0
for i in ids:
    va, vb = values(a[i]), values(b[i])
    for f in FIELDS:
        if va[f] != vb[f]:
            if f != "status":
                flips += 1
            print(f"  {i} {f:<17} {va[f]!r} -> {vb[f]!r}")
print(f"Field flips (excluding status): {flips} of {len(ids) * (len(FIELDS) - 1)}")
