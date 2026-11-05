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
