## Task B4 - Final engineering decision (5 marks)

### B4.1 Practical sentiment, summary and chatbot
TaskB4/complaints.json contains 50 distinct, multi-sentence synthetic complaints. Before running the scorer, an illustrative reference sentiment and salient-sentence position were specified for each. These are illustrative reference judgements, not an independently annotated benchmark. The student must perform the requested own-reading comparison; personal_review.csv provides blank columns for that work without inventing answers.

The implemented lexicon agrees with 31/50 illustrative labels (62%). Frequency-based one-sentence summaries select the nominated salient sentence in 11/50 cases (22%), compared with 7/50 (14%) for the first sentence. This strict exact-sentence measure penalises equally reasonable alternate sentences and is not a complete semantic quality metric. Even so, the low figures reveal that both baselines miss context and cannot be trusted as autonomous complaint triage.

The following table makes every comparison auditable. Key-sentence positions are one-based here; JSON stores zero-based indices. The full texts, predicted scores and both generated summaries are in evaluation.json.

| ID | Reference | Prediction | Agree | Key sentence | Freq hit | First hit |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | positive | positive | Yes | 2 | No | No |
| 2 | positive | positive | Yes | 2 | No | No |
| 3 | positive | positive | Yes | 2 | No | No |
| 4 | positive | positive | Yes | 2 | No | No |
| 5 | positive | positive | Yes | 1 | Yes | Yes |
| 6 | negative | negative | Yes | 2 | No | No |
| 7 | negative | negative | Yes | 2 | No | No |
| 8 | negative | negative | Yes | 2 | No | No |
| 9 | negative | negative | Yes | 2 | No | No |
| 10 | negative | negative | Yes | 2 | No | No |
| 11 | negative | negative | Yes | 1 | Yes | Yes |
| 12 | negative | negative | Yes | 2 | No | No |
| 13 | negative | negative | Yes | 1 | Yes | Yes |
| 14 | negative | negative | Yes | 2 | No | No |
| 15 | negative | negative | Yes | 2 | No | No |
| 16 | positive | positive | Yes | 1 | Yes | Yes |
| 17 | positive | positive | Yes | 1 | Yes | Yes |
| 18 | positive | positive | Yes | 1 | Yes | Yes |
| 19 | positive | positive | Yes | 2 | No | No |
| 20 | positive | positive | Yes | 2 | No | No |
| 21 | neutral | neutral | Yes | 2 | No | No |
| 22 | neutral | neutral | Yes | 2 | No | No |
| 23 | neutral | neutral | Yes | 2 | No | No |
| 24 | neutral | neutral | Yes | 2 | No | No |
| 25 | neutral | neutral | Yes | 2 | No | No |
| 26 | negative | negative | Yes | 2 | Yes | No |
| 27 | negative | negative | Yes | 2 | Yes | No |
| 28 | negative | negative | Yes | 2 | Yes | No |
| 29 | negative | positive | No | 2 | No | No |
| 30 | negative | positive | No | 1 | No | Yes |
| 31 | positive | negative | No | 2 | No | No |
| 32 | negative | positive | No | 2 | No | No |
| 33 | positive | negative | No | 2 | Yes | No |
| 34 | positive | negative | No | 2 | No | No |
| 35 | negative | positive | No | 2 | No | No |
| 36 | negative | positive | No | 3 | No | No |
| 37 | positive | neutral | No | 3 | No | No |
| 38 | neutral | neutral | Yes | 3 | No | No |
| 39 | negative | neutral | No | 3 | No | No |
| 40 | positive | neutral | No | 3 | No | No |
| 41 | positive | neutral | No | 2 | No | No |
| 42 | negative | neutral | No | 2 | No | No |
| 43 | positive | neutral | No | 2 | No | No |
| 44 | negative | neutral | No | 2 | No | No |
| 45 | negative | neutral | No | 2 | No | No |
| 46 | negative | positive | No | 2 | No | No |
| 47 | negative | positive | No | 2 | Yes | No |
| 48 | positive | positive | Yes | 2 | No | No |
| 49 | positive | negative | No | 2 | No | No |
| 50 | positive | positive | Yes | 2 | No | No |

For example, 'Such helpful staff, they ignored every call' can score positively because helpful is in the lexicon and ignored is not. 'The lane is not not clean' illustrates double-negation failure. 'The old service was bad but the current service is good' cancels to neutral, missing that the later clause and conclusion express satisfaction. The baseline's three possible labels also cannot distinguish factual neutral text from a mixture of strong positive and negative aspects.

The completed exercise preserves its given tokenisation and produces:

```text
positive | Roads are clean and the bus was fast.
negative | Smoke from the factory, air is bad.
negative | The staff were not helpful.
positive | Not bad, service improved.
```

The practical chatbot passes eight tests: valid Adyar, quoted station name, missing readings, two stations, unknown station, invalid calendar date, unsupported intent and absent date. A fixed test clock makes today mean 2026-10-01; the saved answer is a synthetic daily mean with its count, not a live reading. Its answer is checked against an independent sum/count query, and an extractive-summary check verifies that the returned sentence occurs in the original complaint.

### B4.2 Index the database and measure the slowest query
The controlled test uses B3's 1,051,200-row unindexed aq table copied to a separate experiment database. It measures the three A1-style query shapes, records EXPLAIN QUERY PLAN, chooses the slowest baseline by its median, then adds CREATE INDEX idx_station_day ON aq(station,day). Seven warm-query trials are saved for each before/after case. Result equivalence is checked to a floating-point tolerance.

| Query | Before ms | After ms | Before / after |
| --- | --- | --- | --- |
| station_month | 19.9305 | 0.0283 | 703.41x |
| station_comparison | 31.8970 | 28.8034 | 1.11x |
| worst_hours | 32.0026 | 32.4056 | 0.99x |

The baseline slowest query was worst_hours, at about 32.003 ms; after indexing it took 32.406 ms. That is effectively unchanged at this measurement precision, with a small run-to-run variation rather than a demonstrated improvement. It filters only on date and groups by hour, so a station-leading index does not provide a selective station range. The station/month query improved greatly because it can search station equality followed by a day interval; the full-city station comparison improves only modestly. Index construction took 0.196199 seconds, and indexes also occupy disk and add write cost.

This is deliberately a heap-table experiment. B1's PRIMARY KEY (station, day, hour) already creates an index with the required prefix; adding another (station, day) index there would normally duplicate useful access ordering. For the city-wide report, test a date-leading index such as (day, hour, pm25) or a maintained daily/hourly summary rather than assuming every index speeds every query. Those extra production candidates are recommendations for a follow-up workload test, not measured improvements in this report.

### B4.3 Decision at the expanded scale
If only the 100 added stations report every 15 minutes while the original 12 stay hourly, the network produces 100 x 96 + 12 x 24 = 9,888 readings/day, or 3,609,120 in a 365-day year. If all 112 stations switch to 15-minute intervals, it produces 10,752/day and 3,924,480/year. These are around 3.4-3.7 times the largest benchmark, but its timings should not be extrapolated as guaranteed latency: cache, disk, indexes and concurrency change.

Keep immutable raw CSVs plus checksum/provenance, stage and validate each incoming file, record rejected rows, then insert bounded batches transactionally. Replace the hour-only key with an unambiguous timestamp or day/minute slot; the existing hourly schema would wrongly collapse four quarter-hour readings. Track station timezone and schedule, distinguish late corrections from duplicates, and publish per-column coverage and quality flags. Apply validation before accepting data, and fit scaling parameters only on the relevant training/reference period.

SQLite is a practical starting point for this classroom-sized single-writer service and scheduled reports; monitor lock contention, backups, file growth and query latency. If concurrent writers or availability requirements grow, migrate the same validated schema to a server database. Query date ranges, retain station/time indexing, and maintain summary sum/count/min/max so repeated reports do not scan all history. Use pandas on selected extracts for exploratory analysis and matplotlib for labelled reports. The million-row measurements support this workflow, not an untested production capacity guarantee.

The 50-case medians were 0.1611 ms for sentiment, 0.2810 ms for frequency summaries and 0.0448 ms for first-sentence summaries. These short English fixtures show low computational cost; 50,000 monthly complaints are primarily a quality and oversight problem for this baseline. Do not route or dismiss complaints solely from a sentiment sign. Keep the simple scorer as an explainable demonstration, collect representative independently reviewed multilingual labels, evaluate a trained baseline on a held-out test set, and retain human review for uncertain or important cases.

### Alternative: first k sentences
If sentences are already stored in an array, selecting a fixed k sentence references is O(k), conventionally O(1) for fixed k. Producing the copied output still costs its character length. Starting from raw text, this implementation splits the entire complaint before slicing, so first_k is O(W) time/space in input words or characters, not O(1) end-to-end. A streaming implementation could stop after the kth sentence, costing the prefix length.

Frequency counting and sentence scoring cost O(W); the implemented sorting of S sentence scores adds O(S log S), and retained tokens/frequencies use O(W + V + S) space. A top-k heap could reduce selection to O(S log k), but is not used here. On the 50-complaint rubric, frequency improves exact salience matches by four cases, yet both methods remain poor: first sentences often introduce the topic while the actionable detail or overall judgement comes later. Repetition can also mislead the frequency method. The full paired summaries support inspection instead of a claim that frequency always gives better summaries.
