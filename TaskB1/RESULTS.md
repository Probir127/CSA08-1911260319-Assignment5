## Task B1 - Implement and validate the cleaning pipeline (7 marks)

### B1.1 Before/after evidence
TaskB1/small_messy.csv has 21 records. Its first record is Adyar,2026-10-01,0,48,80,15,30,C; the second uses aDyAr with surrounding spaces and a lowercase unit; the third is Guindy at 86 F; the fourth is King's Park. The remaining 17 records deliberately introduce each row-level fault listed in A1.1. The original rows, accepted rows and full rejection messages are preserved in small_before_after.json, and small_cleaned.csv is directly inspectable.

Accepted records after canonicalisation and conversion:

| Station | Date/hour | PM2.5 | PM10 | NO | Celsius |
| --- | --- | --- | --- | --- | --- |
| Adyar | 2026-10-01/0 | 48.00 | 80.00 | 15.00 | 30.00 |
| Adyar | 2026-10-01/1 | 60.00 | 90.00 | 20.00 | 31.00 |
| Guindy | 2026-10-01/0 | 95.00 | 150.00 | 25.00 | 30.00 |
| King's Park | 2026-10-01/0 | 40.00 | 70.00 | 10.00 | 29.00 |

Rejected records (line numbers include the header):

| CSV line | Reason |
| --- | --- |
| 6 | missing pm25 |
| 7 | missing pm10 |
| 8 | no outside 0..999 |
| 9 | pm25 outside 0..999 |
| 10 | could not convert string to float: 'broken' |
| 11 | non-finite pm25 |
| 12 | non-finite pm25 |
| 13 | temperature outside -50..60 C |
| 14 | day is out of range for month |
| 15 | Invalid isoformat string: '01/10/2026' |
| 16 | hour outside 0..23 |
| 17 | hour must be an integer |
| 18 | unknown or empty station |
| 19 | temperature unit disagrees with station metadata |
| 20 | duplicate station/day/hour; first valid row retained |
| 21 | wrong number of columns |
| 22 | wrong number of columns |

All 17 faulty records are rejected; all four expected valid records are retained. Checks also cover empty/constant scaling, exact Fahrenheit conversion, a case-normalised station, and z-score mean approximately zero. For accepted PM2.5 values [48,60,95,40], min-max gives approximately [0.145455,0.363636,1.000000,0.000000]. The normalisation functions preserve full precision; display rounding is separate.

### B1.2 Implementation compared with the design
The design's complete-case rejection, source-order duplicate policy, trusted station units and separate rejection ledger are implemented without changing their meaning. The file reader uses UTF-8 with optional BOM support; a broken header, CSV quoting or encoding fails the entire acquisition call instead of returning a silently partial file. The small script retains rows and errors in memory to make the evidence reviewable, so its memory is O(n); a production implementation should write batches and stream its error ledger.

The specified Complete the Code exercise is deliberately separate: it has only station/date/pm25 columns and filters valid non-negative PM2.5. Its TODO regions are filled, the original example output matches, and the required above-999 assertion uses an added 1000 test row. It does not pretend to be the full eight-column production validator.

```text
[('Adyar', '2026-10-01', 48.0), ('Guindy', '2026-10-01', 95.0), ('Guindy', '2026-10-03', 121.0)]
[0.0, 0.644, 1.0]
Above-999 row skipped: PASS
```

### B1.3 Store and query
The monthly generator creates 8,928 hourly observations for 12 stations over 31 days. Forty-eight contain missing PM2.5; 8,880 are accepted. The database contains 372 station/day summaries with 23 or 24 accepted readings per day. The stored units and checks follow A1, and executemany inserts all accepted records in a transaction.

The three implemented SQL questions are:

```sql
SELECT AVG(pm25), COUNT(*) FROM readings
WHERE station = ? AND day >= ? AND day < ?;

SELECT station, AVG(pm25), COUNT(*) FROM readings
WHERE day >= ? AND day < ?
GROUP BY station ORDER BY AVG(pm25) DESC;

SELECT hour, AVG(pm25), COUNT(*) FROM readings
WHERE day >= ? AND day < ?
GROUP BY hour ORDER BY AVG(pm25) DESC, hour LIMIT 5;
```

Bind Adyar/2026-10-01/2026-11-01 for question 1 and the same two date bounds for questions 2 and 3. Adyar's monthly mean is 40.6632 micrograms/m3 over 740 readings. The station comparison is:

| Station | October mean PM2.5 | Valid readings |
| --- | --- | --- |
| King's Park | 73.6489 | 740 |
| Porur | 70.6692 | 740 |
| Tambaram | 67.6692 | 740 |
| Mylapore | 64.6692 | 740 |
| Royapuram | 61.6692 | 740 |
| Perambur | 58.6692 | 740 |
| Ambattur | 55.6875 | 740 |
| Anna Nagar | 52.6875 | 740 |
| T Nagar | 49.6632 | 740 |
| Velachery | 46.6389 | 740 |
| Guindy | 43.6389 | 740 |
| Adyar | 40.6632 | 740 |

The top five mean hours are 20, 19, 8, 18 and 7, respectively, with means 70.6963, 70.6801, 70.6746, 70.6639 and 70.6584 micrograms/m3. Every one has 370 valid observations across stations/days. The tiny ranking differences reflect the deterministic missing-value pattern; hour 9 also belongs to the generator's high-reading band.

### B1.4 Four charts and interpretation
![Monthly trend](TaskB1/trend.png)

Adyar's daily mean rises from 33.57 on October 1 to 49.58 on October 31, with intermediate oscillations. Guindy follows a similar shape at a higher level because both share the same synthetic time pattern; this is evidence that the plotting pipeline works, not a discovery about the real city.

![Station comparison](TaskB1/stations.png)

King's Park has the largest synthetic monthly mean (73.6489), and Adyar the smallest (40.6632). Every station has 740 valid readings, so coverage is equal in this fixture; a real comparison should inspect unequal coverage and missing-data patterns before ranking stations.

![Temperature relationship](TaskB1/scatter.png)

The scatter contains broad bands and substantial PM2.5 variation at similar temperatures. Both variables are generated from time-related formulas; the chart supports neither a simple causal relationship nor a claim that temperature alone predicts pollution.

![Hourly distribution](TaskB1/hours.png)

The distributions at hours 7-9 and 18-20 are shifted upward relative to other hours, matching the generator's 18-unit addition. Overlapping boxes show substantial variation across dates and stations, so a worst-hour ranking of means does not describe every individual reading.

### Alternative: csv loops versus pandas
The timed comparison isolates the exercise's PM2.5 column cleaning and min-max scaling on identical generated three-column files. Each file includes 10% NA, 10% blank, 10% negative, 10% above 999 and 60% valid readings; both methods agree on valid count, sum and normalized sum. Full date/unit/duplicate validation is outside this microbenchmark, so these times are not claimed as timings of every B1 rule.

The loop reads csv.DictReader rows, filters and stores floats, then scales them. pandas read_csv, replace, to_numeric, dropna, between and vectorised arithmetic perform the equivalent operations. Both are O(n) time and O(n) retained-data memory; pandas uses additional arrays/masks and DataFrame storage. Chunked pandas or streamed batches would change the memory model, but were not benchmarked.

| Rows | csv loop ms | pandas ms | Loop peak MiB | pandas peak MiB |
| --- | --- | --- | --- | --- |
| 1000 | 0.506 | 1.859 | 28.6 | 72.8 |
| 100000 | 46.622 | 24.672 | 32.6 | 89.6 |
| 1000000 | 471.518 | 230.022 | 75.9 | 208.5 |

The values are three-run medians in milliseconds; memory is the maximum process peak RSS across the runs in MiB. Each trial runs in a fresh process. Imports are excluded from elapsed time, while RSS includes interpreter and imported libraries; peak RSS is not just the DataFrame's byte size and is platform-specific. Files are likely warm in the operating-system cache. pandas is slower for 1,000 rows because its setup costs dominate, but approximately twice as fast at one million rows while using substantially more process memory. All raw runs are in cleaning_benchmarks.json.
