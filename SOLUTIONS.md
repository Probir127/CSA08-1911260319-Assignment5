# CSA08 - Assignment 5 - CO5 Worked Solutions

## Submission details and scope

Student: PROBIR SAHA SHOHOM. Register number: 1911260319. Course: CSA08 - Python Programming. Total marks: 50. Repository: https://github.com/Probir127/CSA08-1911260319-Assignment5.

This report covers A1-A5 (25 marks) and B1-B4 (25 marks), including all three Complete the Code exercises. It follows acquire, inspect, clean, normalise, store, query, visualise, profile and interpret. The code, source fixtures, generated charts, SQLite database, raw timings and output transcripts accompany the report.

All datasets are explicitly synthetic. Measurements were actually executed in the recorded local environment; they vary across hardware and runs. The student should review, personally run and understand the work, capture the execution screenshots required by the brief, complete their own complaint-label review and share the repository with the faculty. The included output images render captured stdout and are labelled accordingly; they are not terminal screenshots. 

Part A uses structured ALGORITHM, INPUT, OUTPUT, BEGIN/END, IF/ENDIF and FOR/ENDFOR pseudocode. The source names a SIMATS standard but does not attach its detailed template, so exact conformity to an unavailable institutional template is not claimed. The algorithms are language-independent; Python source is provided separately for Part B.

## Environment and evidence map

Python 3.12.14; pandas 2.2.3; NumPy 2.3.5; matplotlib 3.11.2; SQLite 3.53.1; macOS 27.0 on arm64. requirements.txt pins the external libraries actually used. Standard-library modules include csv, io, sqlite3, statistics, re, logging, time, timeit, cProfile, pstats, resource, subprocess, pathlib, datetime and json.

| Task | Main deliverables |
| --- | --- |
| A1-A5 | One task folder per design, pseudocode and complexity comparison |
| B1 | pipeline.py, demo.py, complete_code.py, messy/clean CSVs, SQLite, four charts, timings |
| B2 | adversarial.py, complete_code.py, malformed fixtures, SQL and logging experiments |
| B3 | benchmarks.py, generator, three-size timings, full profile, agreement checks |
| B4 | ai.py, complete_code.py, 50 complaints, paired summaries, chatbot, index experiment |

## Task A1 - Design the data acquisition (7 marks)

### A1.1 Source structure and expected problems
One UTF-8 CSV contains a header followed by hourly readings. The exact columns are station,date,hour,pm25,pm10,no,temperature,temp_unit. One example is Adyar,2026-10-01,0,48,80,15,30,C. PM2.5, PM10 and NO use micrograms/m3; NO denotes nitric oxide, not NO2. Temperature uses the declared C or F unit. The sample network has 12 stations, with Guindy and Ambattur configured for F. All measurements and complaints supplied with this solution are synthetic teaching fixtures, not observations from the city.

The added station and unit columns make the source self-describing. In a real deployment, a trusted station manifest could supply them when the incoming CSV omits them. That adapter must validate the filename/station mapping rather than infer a unit from how large a temperature looks.

| Problem | Example | Implemented treatment / evidence |
| --- | --- | --- |
| Missing number | blank PM2.5; PM10 = NA | Reject incomplete row; small_messy.csv |
| Negative pollutant | NO = -1 | Reject; concentrations cannot be negative |
| Implausibly high value | PM2.5 = 1000; temperature = 61 C | Reject against declared sensor limits |
| Non-numeric or non-finite | broken, nan, inf | Reject before arithmetic |
| Duplicate key | Adyar, 2026-10-01, hour 0 repeated | Keep first valid row and log duplicate |
| Date malformed or impossible | 01/10/2026; 2026-02-30 | Require a valid ISO calendar date |
| Hour invalid | 24; 1.5 | Require integer 0 through 23 |
| Station whitespace/case | two spaces, aDyAr, two spaces | Canonicalise to Adyar through registry |
| Unknown station | Unknown or empty | Reject, rather than invent a station |
| Fahrenheit or unit conflict | Guindy 86 F; Adyar declared F | Convert registered F to 30 C; reject conflict |
| Row-width mismatch | missing unit; extra ninth field | Reject and log row |
| Header/delimiter wrong | missing pm10; semicolons | Reject whole file, explicit SourceError |
| Wrong encoding | Latin-1 accented station | Reject file as UTF-8 decoding failure |
| Empty file / invalid CSV syntax | no header; unclosed quote | Reject whole file |
| Quote in legitimate station | King's Park | Accept; bind value in SQL parameters |

Malformed records, missing columns, wrong delimiters and encoding problems are separately exercised in B1 and B2. Empty lines are skipped by csv.DictReader; they are not observations. Thousands separators and localized date formats are outside this source contract and are not silently guessed.

### A1.2 SQLite design and mapping
The stations table has station TEXT PRIMARY KEY and temperature_unit TEXT NOT NULL constrained to C/F. The readings table has station TEXT NOT NULL as a foreign key, day TEXT NOT NULL, hour INTEGER NOT NULL, pm25 REAL NOT NULL, pm10 REAL NOT NULL, no REAL NOT NULL, and temperature_c REAL NOT NULL. Its composite primary key is (station, day, hour); SQL CHECK constraints reinforce hour and measurement ranges. Foreign keys are enabled for the load connection.

CSV station maps through the canonical registry; date maps to day; hour maps to an integer; three pollutants map to finite REAL values; temperature/temp_unit map to temperature_c after conversion. Unit metadata belongs to stations and is not repeated in each cleaned reading. Raw files and a separate JSON rejection ledger preserve the original input and reasons. Dates are validated by Python before insertion; TEXT alone does not enforce a calendar date.

A daily_summary view groups readings by station and day. A production ingestion ledger should additionally store source file, checksum, ingestion time and rule version. The demonstration loader deliberately rebuilds its own output database on each run; it is not an incremental production loader.

```text
ALGORITHM ACQUIRE_AND_STORE
INPUT: source file, station registry, destination database
OUTPUT: validated readings, rejection ledger, database
BEGIN
    OPEN source AS UTF-8 CSV
    IF header does not match required fields THEN
        REPORT file error
        STOP
    ENDIF
    INITIALISE accepted records, rejection ledger, seen keys
    FOR EACH numbered source record DO
        VALIDATE AND NORMALISE record using cleaning rules
        IF record is invalid THEN
            APPEND line and reason TO rejection ledger
        ELSE IF record key is in seen keys THEN
            APPEND duplicate reason TO rejection ledger
        ELSE
            ADD record key TO seen keys
            APPEND cleaned record TO accepted records
        ENDIF
    ENDFOR
    CREATE stations and readings tables
    INSERT station metadata using bound parameters
    INSERT accepted records using one batch operation
    COMMIT transaction
    RETURN accepted records, rejection ledger, database
END
```

### A1.3 Three board questions: CSV versus SQL
Question 1: What is Adyar's average PM2.5 in October 2026? CSV processing scans every relevant file, filters station/date, and maintains sum/count. SQL uses AVG(pm25), COUNT(*) with station=? AND day>=? AND day<?. The half-open interval ends at 2026-11-01, avoiding accidental November data.

Question 2: How do stations compare in October? CSV uses a dictionary of station sums/counts, or pandas groupby. SQL filters the month, groups by station, and orders AVG(pm25) descending. Question 3: Which five hours have the largest October mean PM2.5? CSV groups by hour; SQL GROUP BY hour orders the mean descending and takes LIMIT 5. A tie uses hour ascending in the B1 query.

Loading all CSVs into a pandas DataFrame for every question costs O(n) parsing time and O(n) working memory, before the aggregation; materialized copies increase constants. A streaming CSV sum/count answer can use O(1), O(stations), or O(24) auxiliary memory, but still scans O(n) records. SQLite holds O(n) rows plus indexes on disk and can return small result sets without loading the entire table into Python.

The assignment's approximate O(log n) index lookup is only the search component. A station/month average must also read k matching values: roughly O(log n + k) with an appropriate index/covering access path, not O(log n) for the entire average. A station-leading index does not automatically accelerate a date-only city-wide query. B4 tests that distinction; plan details and all query results are saved. SQLite's primary-key index already begins with (station, day), so a duplicate index on that prefix is unnecessary in B1.

## Task A2 - Design the cleaning and normalisation (5 marks)

### A2.1 Rules and justification
The chosen baseline drops a row if any required numeric reading is blank, NA, malformed, non-finite or outside the sensor range. Keeping only complete observations makes downstream comparisons consistent and avoids treating invented values as measured concentrations. It can bias averages if failures occur during pollution spikes; therefore every daily mean must be accompanied by the valid count and coverage. The alternative of retaining partially valid rows with per-column counts is useful, but is not the implemented complete-case policy.

Assumed sensor acceptance limits are PM2.5 0..999, PM10 0..1999, NO 0..999 micrograms/m3, and temperature -50..60 C after conversion. These are demonstration validation bounds, not health thresholds or verified specifications for real instruments. Missing or impossible values are not replaced with zero. An unknown station, invalid timestamp or unit conflict rejects the record because it cannot be attributed reliably.

A duplicate means the same canonical station, date and hour, even if the readings differ. Keep the first valid row in source order and log later duplicates; an earlier invalid row never reserves its key. A real correction protocol should retain versions instead of blindly overwriting data. Fahrenheit conversion is C = (F - 32) * 5 / 9; both the row unit and trusted station metadata must agree.

Forward fill could retain a station's last valid value, only after sorting its readings by timestamp and limiting the gap length; never fill across stations. It risks hiding abrupt changes. A station/month median is less sensitive to outliers than a mean but flattens variation and can leak future information into an online task. A training model must fit imputation statistics only on its training window. Any imputed values should carry flags.

### A2.2 Min-max and z-score
For finite values x, min-max scaling is (x - minimum)/(maximum - minimum); z-score is (x - mean)/population_standard_deviation. Min-max is useful when a model expects comparable bounded training features; z-score expresses distance from the mean and is useful when relative variation matters. Neither method makes a skewed distribution normal or repairs bad data, and min-max is sensitive to outliers.

The functions return an empty list for no data and zeros for a constant series, avoiding division by zero. Fit a shared reference interval when comparing stations; independently rescaling each station would erase absolute differences. Save the fitted parameters for future inputs; future min-max values can fall outside 0..1 and should be investigated, not silently clipped. Raw concentrations remain in SQLite; scaling is a derived analysis feature, not a replacement for units.

```text
ALGORITHM NORMALISE_PM25
INPUT: validated finite values
OUTPUT: scaled values and standardised values
BEGIN
    IF there are no values THEN
        RETURN two empty lists
    ENDIF
    COMPUTE minimum, maximum, mean and population deviation
    FOR EACH value DO
        IF maximum equals minimum THEN SET scaled TO 0
        ELSE SET scaled TO (value - minimum) / (maximum - minimum)
        ENDIF
        IF deviation equals 0 THEN SET standardised TO 0
        ELSE SET standardised TO (value - mean) / deviation
        ENDIF
        APPEND results TO output lists
    ENDFOR
    RETURN output lists
END
```

### A2.3 Standard formatting and alternative complexity
Use YYYY-MM-DD dates, local integer hours 0..23, station registry spelling, UTF-8 CSV with a header, Celsius and the stated pollutant units. Retain full floating-point precision for calculation; display means and charts to sensible precision and CSV summaries to four decimal places. Binary floats are approximate, so correctness comparisons use a tolerance.

Dropping costs O(n) after parsing; streaming rejection can use O(1) auxiliary state, although this implementation retains accepted rows, seen keys and errors and therefore uses O(n) memory. Forward fill after timestamp ordering is O(n), with O(stations) last-value state; sorting unsorted inputs adds O(n log n) time and typically O(n) storage. A median obtained by sorting costs O(m log m) for each station group and O(n) total retained values; selection algorithms can do better, but that is not the sorting-based alternative requested.

For observations [10, missing, missing, 90], dropping gives mean 50 with only 2/4 valid samples; forward fill gives [10,10,10,90] and mean 30; median fill gives [10,50,50,90] and mean 50. None proves the missing observations were 10 or 50. This example shows why the report records coverage and does not call imputed values valid measurements.

## Task A3 - Design the analysis and visualisation (5 marks)

### A3.1 Chart choices
| Board question | Chart and axes | Reason |
| --- | --- | --- |
| PM2.5 trend over a month | Line: date versus daily mean PM2.5; separate Adyar/Guindy lines | Preserves chronological order and makes rises/falls visible without 12 overlapping traces |
| Compare stations | Horizontal bar: station versus monthly mean PM2.5 | Direct ranking; long station names remain readable |
| Temperature versus PM2.5 | Scatter: Celsius versus PM2.5 for Adyar | Shows spread and possible association; restricting station reduces one source of confounding |
| Hours with worst air | Box plot: local hour versus PM2.5 distribution | Shows median, variability and overlap for each hour; complements the top-five mean query |

A histogram of concentrations would answer how often concentrations occur, not which clock hours have the worst air. An hourly bar of means is another reasonable choice, but it hides spread; the box plot is used here. Label data as synthetic and retain physical units. Do not infer causation, health risk categories, or real-city trends from these generated charts.

### A3.2 Daily summary table
Each row is keyed by station/day and contains minimum, maximum, mean and valid_count. The implemented daily_summary view derives these fields through MIN, MAX, AVG and COUNT over accepted records. The CSV is ordered by station/day. Hourly full-day expected_count is 24, so coverage is valid_count/24 when the station was scheduled for the entire day. A future production summary should join a station/day calendar to display zero-count days explicitly; the current view produces no row for a day with zero accepted readings.

For missing readings, count means accepted observations, not scheduled observations. A network-wide daily mean weights the available readings; an equal-station average is a different statistic and must be named separately. If daily summaries are combined into a monthly mean, weight by their counts or retain sum/count; taking an unweighted average of daily means can give the wrong answer when coverage differs.

```text
ALGORITHM DAILY_SUMMARY
INPUT: validated records
OUTPUT: summary keyed by station and day
BEGIN
    INITIALISE empty group dictionary
    FOR EACH record DO
        SET key TO record station and day
        IF key is new THEN
            INITIALISE sum TO 0, count TO 0
            INITIALISE minimum AND maximum TO record PM2.5
        ENDIF
        ADD record PM2.5 TO group sum
        INCREMENT group count
        UPDATE group minimum AND maximum
    ENDFOR
    FOR EACH group DO
        SET mean TO sum / count
        OUTPUT station, day, minimum, maximum, mean, count
    ENDFOR
END
```

The running-dictionary version is expected O(n) time and O(g) group state for g station/day groups. Reading all rows and storing lists before statistics.mean remains O(n) time but O(n) values plus O(g) metadata. SQL GROUP BY must also inspect relevant values; it is not automatically O(log n). Depending on its plan, ordered grouping can scan O(n), while sorting may cost O(n log n) with temporary storage that can spill to disk. B3 measures the actual SQLite plan's workload rather than assuming a universal winner.

## Task A4 - Plan debugging and profiling (4 marks)

### A4.1 Debugging plan
Start with the hand-checkable four accepted records and seventeen rejects. Print a small raw/clean pair and reject reason while diagnosing a defect. Use assertions for developer invariants: known 86 F -> 30 C, normalisation of a constant series, query agreement, valid counts, and expected fixture results. Assertions supplement explicit input validation; they can be disabled with optimisation, so input safety must never depend on them.

The pipeline uses a named logger for accepted/rejected counts, while structured ledgers preserve row numbers and reasons. Configure INFO during a diagnostic run and WARNING for routine operation. Log lazily with placeholders to avoid eager formatting when the message is disabled; avoid logging an entire sensitive complaint in a production system. Set a debugger breakpoint inside the rejected-row handler, inspect raw/line/unit/temperature, and step through conversion or date validation. The supplied runnable checks are the evidence; an interactive pdb session is a plan, not a claimed captured execution.

```text
ALGORITHM DEBUG_A_REJECTED_READING
INPUT: smallest failing source record and expected outcome
OUTPUT: explained defect or confirmed rejection
BEGIN
    REPRODUCE failure using the small input
    PRINT only the raw record and observed outcome
    SET breakpoint immediately before validation
    INSPECT parsed fields, station metadata and conversion result
    STEP through the first failing condition
    COMPARE observed behaviour WITH the explicit cleaning rule
    CORRECT the implementation only if the rule is violated
    RUN the small regression check and the complete pipeline checks
    KEEP rejection counts in logging; remove temporary prints
END
```

### A4.2 Profiling plan and print-only alternative
Use time.perf_counter around complete operations with clear boundaries. Use timeit.repeat or repeated timeit.timeit for small stable functions, keeping data generation and imports outside the timed block. Use cProfile on the plain-Python daily mean calculation, then inspect both cumulative time and internal time; a top-level wrapper's cumulative time includes its children and does not identify the deepest bottleneck by itself.

B1/B3 run three fresh subprocess trials per size/method and report medians plus all raw values; import time is excluded, but process peak RSS includes imports. B2 runs five insertion trials, three timeit trials of 10,000 debug calls, and compares identical transaction policies. B4 warms each query and uses seven trials before/after indexing. These are local repeated measurements, not confidence intervals or guarantees for another computer.

A print-only solution can use IF debug_enabled THEN PRINT state, but offers less selective control than logger levels and cannot inspect the live stack like a debugger. n fixed-length printed messages add O(n) work and O(total message bytes) output; terminal rendering can dominate runtime. Enabled logging also formats and emits O(n) messages and may cost more per call. Disabled logging still incurs n function/level checks, and arguments evaluated before the call still cost time. For very expensive diagnostic preparation, guard it with isEnabledFor or a debug flag. Remove temporary print calls or guard them; switch logging off by raising the level, and remove breakpoints before routine execution. The B2 timing uses StringIO, so it does not claim to measure interactive terminal latency.

## Task A5 - Design an AI application for citizen complaints (4 marks)

### A5.1 Sentiment and extractive summary
The sentiment baseline tokenises lowercase words and assigns +1 to good, clean, fast, helpful and improved; -1 to bad, dirty, slow, rude, smoke and broken. A directly preceding not, never or no flips the word's sign. Positive totals give positive, negative totals negative, and zero neutral. The practical function keeps sentence boundaries, so a negator cannot cross a sentence; the separately completed exercise preserves the supplied simpler tokenisation.

For an extractive summary, split the complaint into sentences, remove a declared set of stop words from each, count important-word frequencies across that complaint, and score a sentence by the average frequency of its important words. Select the top k with original position as the tie-breaker, then restore original order. Frequency weighting is a heuristic: repeated boilerplate can outrank a critical sentence. Extraction copies source sentences and does not invent new wording, but can omit context, negation or the speaker's main concern.

```text
ALGORITHM SENTIMENT_SCORE
INPUT: complaint, positive words, negative words, negators
OUTPUT: sentiment label and numeric score
BEGIN
    SET total TO 0
    FOR EACH sentence IN complaint DO
        TOKENISE sentence into lowercase words
        FOR EACH word with its position DO
            SET value TO 1 if positive, -1 if negative, otherwise 0
            IF preceding word is a negator THEN
                SET value TO negative value
            ENDIF
            ADD value TO total
        ENDFOR
    ENDFOR
    RETURN positive if total > 0, negative if total < 0, otherwise neutral
END

ALGORITHM EXTRACTIVE_SUMMARY
INPUT: complaint and requested sentence count k
OUTPUT: selected original sentences
BEGIN
    SPLIT complaint into sentences
    IF k <= 0 THEN RETURN empty summary
    ENDIF
    TOKENISE each sentence and REMOVE stop words
    COUNT important-word frequencies across the complaint
    COMPUTE each sentence's average important-word frequency
    RANK sentences by decreasing score, then original position
    SELECT at most k sentences and RESTORE source order
    RETURN selected source sentences
END
```

### A5.2 Rule-based chatbot and limitations
The chatbot accepts PM2.5/PM25, exactly one registered station and either today or an ISO date. It rejects ambiguous station/date requests, validates the calendar date, and executes a parameterised average/count query. An empty result becomes 'No valid readings', never zero pollution. Its reply includes the station, date, mean, physical unit and count. The demonstration fixes today to 2026-10-01 solely for reproducibility; normal execution uses the current date.

```text
ALGORITHM ANSWER_PM25_QUESTION
INPUT: question, station registry, database, current date
OUTPUT: factual answer or clarification
BEGIN
    IF PM2.5 intent is absent THEN RETURN supported-question guidance
    ENDIF
    MATCH registered station names at word boundaries
    IF not exactly one station matches THEN RETURN clarification
    ENDIF
    RESOLVE one explicit valid date OR today
    IF a date cannot be resolved THEN RETURN clarification
    ENDIF
    QUERY average and count using bound station and date parameters
    IF count equals 0 THEN RETURN no-valid-readings message
    ENDIF
    RETURN station, date, mean, unit and valid count
END
```

This system does not understand arbitrary synonyms, Tamil or other languages, misspellings, yesterday/last week, subtle negation, sarcasm, or causal and health questions. The demonstration returns a daily mean, not the latest instantaneous measurement. A complaint with both positive and negative aspects can sum to neutral even when its final opinion is clearly negative.

A trained Naive Bayes alternative would collect independently labelled examples, split training/validation/test data, fit a tokenizer and vocabulary, estimate class priors and token likelihoods, then evaluate macro-F1 and per-class errors on held-out complaints. Inference is roughly O(W*C) for W tokens and C classes, with O(V*C) model memory. The fixed lexicon is O(W) time and O(V_lexicon) dictionary memory, aside from token lists; it needs no training. A language model uses substantially more model memory and compute, with costs depending on architecture and input length. Better accuracy is possible, not guaranteed; domain, language, annotation quality and distribution shift must be tested. No trained-model accuracy is claimed here because no labelled city corpus or model experiment was supplied.

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

## Task B2 - Engineer adversarial data (5 marks)

### File and SQL challenges
The files in TaskB2/inputs are deliberately constructed, then passed through the same clean_file entry point. The program raises SourceError with an explicit cause; the caller records the failure and can continue to a different source. A bad file is not reported as a successful zero-reading day.

| Input | Observed outcome |
| --- | --- |
| empty.csv | expected exact comma-separated header: station,date,hour,pm25,pm10,no,temperature,temp_unit |
| latin1.csv | UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe1 in position 56: invalid continuation byte |
| missing_column.csv | expected exact comma-separated header: station,date,hour,pm25,pm10,no,temperature,temp_unit |
| unclosed_quote.csv | Error: unexpected end of data |
| wrong_delimiter.csv | expected exact comma-separated header: station,date,hour,pm25,pm10,no,temperature,temp_unit |

The missing-column and delimiter tests show why an explicit schema contract is necessary. The encoding test shows that decoding is part of acquisition, not an incidental display choice; a production adapter can accept a documented alternate encoding, but automatic guessing could corrupt names. The empty-file test distinguishes missing observations from actual zero pollution. The unclosed-quote test shows that structural CSV corruption is a file-level failure.

A legitimate station called King's Park illustrates the quoting problem. Concatenation builds WHERE station='King's Park', and SQLite raises OperationalError near s. A placeholder query with that exact station string returns 40.0. Parameter binding lets an apostrophe remain data.

For Adyar' OR '1'='1, string concatenation changes the WHERE clause into a tautology and the unsafe AVG query returns 61.0, the average of all three test stations (48,95,40). Binding the same text with ? searches for that complete literal name, which does not exist, so AVG returns SQL NULL, exposed as Python None. This is not an error and it is not zero. The result is one aggregate row, rather than every raw row; a SELECT * version of the unsafe query would reveal all matching raw rows.

The assignment's separate four-row Complete the Code program produces exactly:

```text
54.0 108.0
None
```

Use placeholders for values, never string interpolation, even when an input looks like a station. Identifier choices such as table or column names require a fixed allowlist because ordinary value placeholders cannot substitute arbitrary SQL syntax. The queries here use fixed identifiers.

### Sentiment adversaries
The four explicit probes are recorded in evidence.json. 'Good, another smoke-filled evening.' scores neutral although the intended sarcastic complaint is negative. 'The road is not not clean.' scores negative, missing the double-negation positive reading. 'Clean park, dirty road.' is neutral and agrees with the balanced mixed reference. 'Helpful staff, broken sensor; overall dissatisfied.' is neutral although the final opinion is negative. These cases expose missing discourse understanding, a one-token negation scope, and a limited lexicon; adding more positive words alone does not solve them.

### Alternative: execute in a loop versus executemany
Both insert n rows and are O(n) time in the unindexed in-memory test; both use a single transaction and a commit after all rows. executemany reduces repeated Python-to-SQL call overhead. With maintained B-tree indexes, insertion can include O(log n) index work per row, and disk/transaction policy can dominate constants. A commit per row would be a different, unfair benchmark.

For 100,000 identical input rows, five-run medians were 33.409 ms for execute in a loop and 18.555 ms for executemany. Both databases were verified to have count 100,000 and PM2.5 sum 24,950,000. The prebuilt input list is O(n); a generator can feed either method with O(1) extra input state, apart from database/cache storage.

### Debug-output experiment supporting A4
For 10,000 calls, median buffered print time was 1.367 ms, disabled debug logging 0.546 ms, and enabled buffered debug logging 21.919 ms. Enabled logging has record construction and formatting overhead; its benefit is controllability and structured severity, not a universal speed advantage. These timeit trials use StringIO and deliberately exclude terminal rendering and disk latency. Logs grow with output bytes; disabled logging avoids building the output buffer.

## Task B3 - Loops versus libraries versus SQL (8 marks)

### B3.1 Correctness and data generation
The generator creates 365 days x 24 hours for 1, 12 and 120 synthetic stations. Station S001 uses index 0. Its hourly PM2.5 formula is 20 + station_index + (day_index MOD 31) + hour/10. Therefore the independent expected daily mean is 20 + station_index + (day_index MOD 31) + 1.15, because the mean of hours 0..23 is 11.5.

The plain baseline collects one list per station/day and calls statistics.mean. The running alternative accumulates a sum and count per key. pandas reads the same CSV and uses groupby(['station','day']).pm25.mean(); SQLite reads a previously loaded database and uses SELECT station,day,AVG(pm25) FROM aq GROUP BY station,day. The small 8,760-row case compares every key/value pair between all four methods. At every size and every repetition, all returned means are also checked against the independent formula, and group counts must be stations x 365. All checks passed, including 43,800 groups at 1,051,200 rows.

### B3.2 Measured time and memory
| Stations | Rows | Lists ms | Running ms | pandas ms | SQL query ms | SQL load ms |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 8,760 | 6.841 | 4.974 | 2.840 | 1.513 | 10.154 |
| 12 | 105,120 | 80.788 | 59.698 | 15.891 | 20.251 | 84.240 |
| 120 | 1,051,200 | 810.374 | 610.721 | 150.563 | 225.650 | 849.702 |

Three independent process trials produce each method median. CSV methods include reading/parsing plus grouping; SQL query timing includes connection, query and result materialisation but excludes initial CSV loading. The separately shown SQL load is one measured parse/batch-insert/commit run, not a three-run median. Add it when comparing one-time end-to-end acquisition; at the largest size the load-plus-query cost is approximately 1.075 seconds. Pre-importing pandas excludes import startup from its time. These boundaries matter more than declaring a library universally fastest.

| Rows | Lists MiB | Running MiB | pandas MiB | SQL MiB |
| --- | --- | --- | --- | --- |
| 8,760 | 28.8 | 28.6 | 78.7 | 29.6 |
| 105,120 | 33.6 | 29.8 | 92.0 | 34.2 |
| 1,051,200 | 86.8 | 48.7 | 198.8 | 46.9 |

Peak RSS includes runtime/import overhead and returned results. At 1,051,200 rows, the running dictionary used approximately 48.7 MiB versus 86.8 MiB for lists and 198.8 MiB for pandas. SQLite process RSS was 46.9 MiB, but its database and temporary storage consume disk space as well; RSS does not measure total storage.

### B3.3 cProfile evidence
The largest plain-Python case produced 13,601,833 function calls in about 1.998 profiled seconds. The top-level mean_lists function has that entire cumulative time; among its hot children csv.DictReader.__next__ takes about 0.849 cumulative seconds and 0.498 internal seconds, while statistics.mean accounts for about 0.837 cumulative seconds. The CSV iterator is the largest internal-time function in this run. Exact-ratio and fraction work under statistics.mean contributes to the aggregation cost.

Profile instrumentation makes the run slower than the unprofiled 0.810-second median, so the profile time is diagnostic evidence, not another directly comparable benchmark. The full cumulative and internal rankings are saved in profile.txt. Replacing per-group lists/statistics.mean with sum/count avoids retaining every float and avoids some exact-arithmetic overhead, while tolerance-based comparison accounts for floating-point summation differences.

### B3.4 Engineering choice and complexity
For a one-time analysis of a moderately sized CSV already fitting memory, pandas is concise and was fastest among these CSV methods. For an automated daily report, ingest each file once into the validated SQLite store and query only the relevant period; repeatedly reparsing the complete history wastes work and complicates consistency. On an environment without pandas or with a strict memory budget, the running dictionary is an effective standard-library fallback.

The list and running algorithms are both expected O(n) time. Lists store O(n) values plus O(g) keys; running sums/counts store O(g), where g = stations x observed days. pandas retains O(n) data plus grouping structures. SQL grouping has plan-dependent sort/index costs and can use temporary disk storage. For this fixed 24-readings-per-group generator, g = n/24, so both n and g grow with the station count: the memory improvement is a real constant reduction here, not evidence of constant memory as the network grows. If the number of observations per fixed group rises, the running-state advantage becomes stronger.

```text
ALGORITHM RUNNING_MEANS
INPUT: CSV readings
OUTPUT: station/day means
BEGIN
    INITIALISE group dictionary
    FOR EACH reading DO
        SET key TO station and day
        INITIALISE sum/count for key if absent
        ADD PM2.5 TO sum
        INCREMENT count
    ENDFOR
    FOR EACH key DO
        OUTPUT key and sum / count
    ENDFOR
END
```

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

## References and final checks

The supplied assignment defines the tasks and marking scheme. Python's sqlite3 documentation describes placeholder binding and executemany: https://docs.python.org/3/library/sqlite3.html. SQLite's Query Planning guide explains index search, multi-column ordering and matching-row work: https://www.sqlite.org/queryplanner.html. pandas documents the split-apply-combine groupby model: https://pandas.pydata.org/docs/user_guide/groupby.html. Library links were checked on 5 November 2026; the executed package versions are listed above and may differ from the latest documentation.

All expected Complete the Code outputs match. The small cleaning fixture, malformed-file checks, SQL injection and quote tests, insertion sums/counts, all-size mean comparisons, eight chatbot cases and index result equivalence passed. Timings, profile and images were generated from actual runs. Remaining student actions are personal execution/screenshots, their own 50-complaint review, conformity with any separately supplied pseudocode template, and sharing/submitting the repository to the faculty. These steps remain for submission.
