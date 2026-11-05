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
