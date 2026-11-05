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
