# Labelling guide: gold_15_TO_LABEL.csv

Fill the 6 empty columns for each row. Use the message timestamp as "today" for that message.

| Column | Allowed values | Rule |
|---|---|---|
| msg_type | promise, dispatch, delivered_claim, excuse, query, other | dispatch = says goods have left (with or without proof). delivered_claim = says goods arrived. If a message has an excuse **and** a new date, it's a promise. |
| material | steel, cement, sand, aggregate, rmc, aac_blocks, electrical, unknown | Only what the message itself names (stone chips/baali count). If it's not named, write `unknown`; the code links it to the open order later. |
| date_direction | future, past, none | "kal aa gaya" = past. "kal aa jayega" = future. If the message has both, label the one about the delivery. |
| promised_date | YYYY-MM-DD, or blank | Only when date_direction = future and a specific day is given. kal = +1, parso/porshu = +2, weekday = next one. "this week" / "jaldi" = blank. "Aaj" counts (= same day). |
| commitment_level | 0, 1, 2, 3 | 0 excuse or no commitment · 1 vague, no date · 2 dated promise (incl. "pakka", incl. "truck nikal gaya" with no proof) · 3 dispatch with evidence (vehicle no., LR/challan no., driver). |
| notes | free text | Anything you were unsure about. These are the most useful for the eval. |

Don't look at any model output before labelling.
