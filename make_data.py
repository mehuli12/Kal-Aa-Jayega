"""Writes the synthetic dataset: messages, receipts (delivery truth), and the 15-message labelling sheet.

Setup: one WhatsApp group per (project, supplier), so supplier and project come from the group
name, not from the model. Window: Mon 19 Oct - Sun 1 Nov 2026. Board is calculated as of Mon 2 Nov 2026.
"""
import csv
import json
from pathlib import Path

DATA = Path(__file__).parent / "data"

PROJECTS = {"P1": "Rajarhat Tower B", "P2": "Salt Lake G+4", "P3": "New Town Mall"}
SUPPLIERS = {
    "S1": "Maa Tara Steel",
    "S2": "Jai Hind Cement",
    "S3": "Ganga Sand & Aggregates",
    "S4": "Shree Balaji RMC & Blocks",
    "S5": "Sen Electricals",
}

# (id, sent_at IST, project, supplier, sender_role, text)
MESSAGES = [
    ("m01", "2026-10-19 10:12", "P1", "S1", "site", "Steel 16mm aur 12mm kab tak? Slab casting Thursday hai."),
    ("m02", "2026-10-19 11:40", "P1", "S1", "supplier", "Sir kal dispatch karenge, parso morning site pe hoga."),
    ("m04", "2026-10-19 12:30", "P1", "S2", "site", "Cement 300 bags urgent chahiye."),
    ("m05", "2026-10-20 09:15", "P1", "S2", "supplier", "Sir kal pakka aa jayega, tension mat lo."),
    ("m07", "2026-10-20 11:00", "P2", "S5", "supplier", "Cable and conduit will reach by 23rd, PO received."),
    ("m06", "2026-10-20 16:20", "P1", "S4", "supplier", "AAC blocks Wednesday tak bhej denge sir."),
    ("m03", "2026-10-20 18:05", "P1", "S1", "supplier", "Truck WB-23-C-4417 nikal gaya, 12 MT TMT (12mm+16mm). Driver Raju 98300-XXXXX. Kal subah 7 baje tak."),
    ("m08", "2026-10-21 10:30", "P2", "S3", "supplier", "Dada, kalke 2 lorry baali pathiye debo."),
    ("m09", "2026-10-21 19:45", "P1", "S2", "site", "Cement nahi aaya aaj. Kya hua?"),
    ("m10", "2026-10-22 08:50", "P1", "S2", "supplier", "Sorry sir, gaadi nahi mili. Kal pakka bhejta hoon."),
    ("m11", "2026-10-22 09:30", "P1", "S1", "supplier", "Sir kal wala truck pahunch gaya na? Challan sign karke bhej dena."),
    ("m12", "2026-10-22 12:10", "P1", "S4", "supplier", "Labour problem chal raha hai sir, 2-3 din lagega."),
    ("m13", "2026-10-23 07:40", "P2", "S3", "supplier", "Kal gari pouchhe gechhe, 2 lorry. Bill pathachhi."),
    ("m14", "2026-10-23 15:00", "P2", "S5", "supplier", "Dispatched today via Sharma Transport, LR no. 55821. Will reach by evening."),
    ("m15", "2026-10-23 18:30", "P2", "S2", "supplier", "Salt Lake site ke liye 200 bags kal aa jayega sir."),
    ("m16", "2026-10-24 11:15", "P1", "S4", "supplier", "Baarish ki wajah se loading nahi hua. Monday ko bhejenge."),
    ("m17", "2026-10-24 14:00", "P1", "S2", "supplier", "Plant mein shortage hai sir. Monday tak ho jayega."),
    ("m18", "2026-10-25 10:05", "P2", "S2", "site", "Kal cement aa gaya tha, 200 bags. Thanks."),
    ("m19", "2026-10-26 09:20", "P1", "S4", "supplier", "Haan sir, woh kal pakka pahunch jayega."),
    ("m20", "2026-10-26 13:40", "P2", "S5", "supplier", "Baaki material jaldi bhej denge sir."),
    ("m21", "2026-10-26 17:00", "P2", "S3", "supplier", "Porshu aggregate pathabo, 20mm."),
    ("m22", "2026-10-27 10:00", "P3", "S1", "site", "Raft ke liye 25mm steel chahiye, Thursday tak."),
    ("m23", "2026-10-27 11:30", "P3", "S1", "supplier", "Done sir, Thursday delivery confirm."),
    ("m24", "2026-10-27 12:45", "P3", "S4", "supplier", "RMC ke liye permit nahi mila abhi. Dekhte hain."),
    ("m25", "2026-10-27 16:10", "P1", "S2", "supplier", "Aaj gaadi pahunch gayi sir, 300 bags."),
    ("m26", "2026-10-28 09:00", "P1", "S2", "site", "Plaster ke liye aur 200 bags cement chahiye."),
    ("m27", "2026-10-28 10:30", "P1", "S2", "supplier", "Woh bhi parso tak aa jayega sir."),
    ("m28", "2026-10-28 12:00", "P2", "S5", "site", "Sen da, baaki cable kab? Electrician bethe hain."),
    ("m29", "2026-10-29 08:15", "P3", "S1", "supplier", "WB-11-D-2290 dispatched, 8 MT 25mm. Driver Manoj. 11 baje tak."),
    ("m30", "2026-10-29 14:20", "P2", "S3", "supplier", "Dada aggregate aaj pouchhe jabe, kal gari kharap chhilo."),
    ("m31", "2026-10-29 16:00", "P3", "S3", "supplier", "New Town e stone chips ei week er moddhe hoye jabe."),
    ("m32", "2026-10-30 10:00", "P1", "S2", "supplier", "Truck nikal gaya hai sir, shaam tak pahunch jayega."),
    ("m33", "2026-10-30 11:30", "P3", "S4", "supplier", "Permit aa gaya sir. Kal pakka RMC bhejenge, 40 cum."),
    ("m34", "2026-10-30 12:00", "P2", "S5", "site", "Sen da? Reply please. 2 din se wait kar rahe."),
    ("m35", "2026-10-31 09:00", "P1", "S2", "site", "Cement kal nahi aaya. Truck kahan hai?"),
    ("m36", "2026-10-31 10:15", "P1", "S2", "supplier", "Checking sir."),
    ("m37", "2026-10-31 17:30", "P3", "S4", "site", "RMC nahi aaya. Pour cancel karna pada."),
    ("m38", "2026-10-31 18:00", "P3", "S4", "supplier", "Sorry sir, pump available nahi tha. Kal subah pakka."),
    ("m39", "2026-11-01 10:00", "P3", "S1", "supplier", "Next lot 25mm Tuesday ko bhejenge sir."),
    ("m40", "2026-11-01 11:00", "P1", "S4", "supplier", "Agla lot blocks Wednesday tak, sir."),
    ("m41", "2026-11-01 12:30", "P2", "S3", "supplier", "Dada, baali r lagbe? Rate barche next week."),
]

# Gate log: what actually arrived. This is the delivery truth, not supplier claims.
RECEIPTS = [
    ("2026-10-21", "P1", "S1", "steel", "12 MT TMT"),
    ("2026-10-22", "P2", "S3", "sand", "2 lorry"),
    ("2026-10-23", "P2", "S5", "electrical", "cable + conduit, first lot"),
    ("2026-10-24", "P2", "S2", "cement", "200 bags"),
    ("2026-10-27", "P1", "S2", "cement", "300 bags"),
    ("2026-10-28", "P1", "S4", "aac_blocks", "1 truck"),
    ("2026-10-29", "P3", "S1", "steel", "8 MT 25mm"),
    ("2026-10-29", "P2", "S3", "aggregate", "20mm, 1 lorry"),
]

# The 15 to label for the eval. Deliberately weighted to the hard cases:
#   "kal" = yesterday: m11, m13, m18, m30   | no material named: m19, m27
#   "pakka" / dispatch claim, no evidence: m05, m10, m19, m32 | real dispatch with evidence: m03
#   Bengali-English dates: m21 (porshu), m31 (ei week)  | excuse / vague: m16, m20, m24
GOLD_IDS = ["m03", "m05", "m10", "m11", "m13", "m16", "m18", "m19",
            "m20", "m21", "m24", "m27", "m30", "m31", "m32"]


def main():
    DATA.mkdir(exist_ok=True)
    msgs = [
        {"id": i, "sent_at": f"{t}+05:30", "project": PROJECTS[p], "supplier": SUPPLIERS[s],
         "chat": f"{PROJECTS[p]} | {SUPPLIERS[s]}", "sender_role": role, "text": text}
        for i, t, p, s, role, text in sorted(MESSAGES, key=lambda m: m[1])
    ]
    (DATA / "messages.json").write_text(json.dumps(msgs, indent=2, ensure_ascii=False))

    with open(DATA / "receipts.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "project", "supplier", "material", "qty"])
        for d, p, s, mat, qty in RECEIPTS:
            w.writerow([d, PROJECTS[p], SUPPLIERS[s], mat, qty])

    by_id = {m["id"]: m for m in msgs}
    with open(DATA / "gold_15_TO_LABEL.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "sent_at", "chat", "sender_role", "text",
                    "msg_type", "material", "date_direction", "promised_date", "commitment_level", "notes"])
        for i in GOLD_IDS:
            m = by_id[i]
            w.writerow([i, m["sent_at"], m["chat"], m["sender_role"], m["text"], "", "", "", "", "", ""])

    print(f"{len(msgs)} messages, {len(RECEIPTS)} receipts, {len(GOLD_IDS)} to label -> {DATA}")


if __name__ == "__main__":
    main()
