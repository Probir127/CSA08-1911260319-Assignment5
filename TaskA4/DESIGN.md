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
