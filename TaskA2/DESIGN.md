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
