# kal-aa-jayega

Turns supplier WhatsApp messages into a delivery-risk board for construction sites.

## Run

```
python3 make_data.py                 # writes data/
python3 extract.py --all             # needs ANTHROPIC_API_KEY; caches to out/extractions.json
python3 eval.py --tag before         # needs data/gold_15_labelled.csv
```

No dependencies beyond the Python standard library.

## Assumptions

- **One WhatsApp group per project + supplier pair**, so supplier and project come from the group name.
  Real sites often run one group per project with several suppliers in it. Supporting that means
  identifying the supplier from the sender and working out which supplier a site engineer's question is aimed at.
- Delivery truth is a gate/receipts log (`data/receipts.csv`), not supplier claims.
- Board is calculated as of 2026-11-02. Message timestamps are IST.
- Text only: no voice notes, photos of challans, or forwarded messages.
- The model never computes dates. It names the reference ("kal", "Monday", "23rd") and `resolve_date()` does the arithmetic.
- The dataset was written by the same AI that extracts it, so accuracy here is optimistic for real chats.

## Known issues (parked after the baseline eval, 2 Nov)

- **Material: group name vs message text.** The model fills material from the chat history or group name
  (e.g. "kal pakka aa jayega" in a cement group → cement). The labels say `unknown` unless the message
  itself names it. This is a guide decision, not a model bug: either label from context too, or keep
  text-only and let the order-linking step fill it in. 6 of 15 disagreements at baseline.
- **Weekday retries.** The model fills `weekday` even when `date_ref` isn't `weekday` (it writes the
  computed delivery day). The validator catches it and the retry fixes it, but 5 of 15 needed a retry at
  baseline. One case (m11) returned the string `"None"` instead of null. Planned fix: a description on the
  `weekday` field, measured by the retry count before and after.
  Retries wobble on their own: an unchanged rerun (noise check) went from 5 to 4 retries (m11 passed first
  time) while 0 of 75 extracted fields changed. So treat a change of ±1 retry as noise.
- **m13 "pouchhe gechhe" read as dispatch.** Bengali "pouchhe gechhe" = has arrived; the model labelled
  it as dispatch (goods have left) instead of delivered_claim.
- **m13 reason invents "baali" (sometimes).** The message doesn't mention sand; the baseline reason said
  "baali (sand)". In the noise rerun "baali" was gone but the reason still said "sand", taken from the chat
  context. So the made-up word is intermittent; naming a material the message doesn't contain is not.
  Reasons are shown on the board, so this would mislead a site manager.
- **m13 reason contradicts its type.** The after-fix reason says the sand "reached", but msg_type is
  still dispatch (goods have left). The reason shown on the board and the type used for scoring disagree.
- **Labelling guide gaps.** No commitment level defined for queries or delivered claims (m18: labelled 2,
  model said 0), and no rule on whether "bhejenge" (will send) gives the send date or the arrival date.

## Eval: before / noise / after (15 labelled messages, claude-haiku-5-5)

**How the labels were made:** drafted with a separate Claude chat, then reviewed and corrected by hand
(`data/gold_15_labelled.csv`). They are not independent hand labels. A model-drafted label can share the
extractor's blind spots, so where the reviewer accepted a draft unchanged, agreement may look better than
it is. Treat these numbers as a check on consistency and on the fix, not as true accuracy.

The one fix: a specific future delivery day means commitment level ≥ 2, "pakka" neither raises nor lowers it
(prompt), plus a validator rule rejecting level 0 or 1 with a specific future day.

| | before (v1) | noise (v1, rerun) | after (v2) |
|---|---|---|---|
| msg_type | 13 | 13 | 14 |
| material | 9 | 9 | 9 |
| date_direction | 15 | 15 | 15 |
| promised_date | 15 | 15 | 15 |
| commitment_level | 10 | 10 | 14 |
| **all fields right** | **6** | **6** | **8** |
| fields changed vs before | – | 0 of 75 | 5 of 75 |
| ok / retried / needs_review | 10 / 5 / 0 | 11 / 4 / 0 | 10 / 5 / 0 |

- All 5 changed fields are on the 4 messages the fix targets: commitment level on m05, m21, m27, m30, and
  m30's msg_type (excuse → promise). The noise rerun changed 0 fields, so the gain is the fix, not variation.
- m30 still came back at level 0 on the first attempt after the prompt change; the new validator rule
  rejected it and the retry fixed it. The prompt alone wasn't enough; prompt + validator was.
- Retries stayed at 5, but which messages retried changed. Most are still the weekday issue (see Known issues).
- Remaining commitment-level miss: m18, a guide gap (site "aa gaya tha"), not a model error.

Reproduce: `python3 extract.py --ids <the 15> --force` then `python3 eval.py --tag <name> --compare before`;
`python3 compare_runs.py <snapshot A> <snapshot B>` counts raw field changes. Run outputs live in `out/` (not committed).

## Next steps

1. **Weekday description.** Add a description to the `weekday` field ("only when the supplier names a weekday;
   null otherwise"), keep the validator strict, and measure retries before/after. Expect a drop well beyond the ±1 noise.
2. **Material rule.** Decide text-only vs chat context in the labelling guide, then make prompt, labels and
   order-linking agree. Fix the guide's other gaps at the same time (level for queries and delivered claims;
   send date vs arrival date for "bhejenge").
3. **Silence signal.** Add "no supplier reply for > 48 h after a site question, on an open order" to scoring.
   Without it the electrical supplier (silent since 26 Oct, 2 of 2 promises kept) looks low-risk.
4. Not built yet in this timebox: supplier reliability and project risk scoring (3 signals: overdue,
   commitment level, reliability) and the HTML board.
