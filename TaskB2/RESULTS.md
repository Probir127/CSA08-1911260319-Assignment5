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
