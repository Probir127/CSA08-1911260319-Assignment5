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
