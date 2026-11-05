# CSA08 - Assignment 5 - CO5

- **Student:** PROBIR SAHA SHOHOM
- **Register number:** 1911260319
- **Course:** CSA08 - Python Programming
- **Title:** Data Acquisition, Cleaning, Analysis and AI Applications
- **Total marks:** 50
- **Repository:** https://github.com/Probir127/CSA08-1911260319-Assignment5

## Environment

Executed with Python 3.12.14, pandas 2.2.3, NumPy 2.3.5, matplotlib 3.11.2 and SQLite 3.53.1 on macOS 27.0 arm64. External dependencies are pinned in `requirements.txt`; the other modules are in the Python standard library. The benchmark's peak-RSS measurement uses `resource` and supports macOS/Linux, not Windows without an adaptation. The core programs can otherwise be used on Python platforms with these libraries.

## Run

Run commands from the repository root in a Python 3.12 environment:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python TaskB1/complete_code.py
python TaskB1/demo.py
python TaskB2/complete_code.py
python TaskB2/adversarial.py
python TaskB3/benchmarks.py --work-dir generated_data
python TaskB4/complete_code.py
python TaskB4/evaluate.py
python TaskB4/chatbot_demo.py
python TaskB4/index_experiment.py generated_data/year_120.sqlite
python verify.py
```

Windows activation differs; the benchmarks require a Unix `resource` module or a replacement RSS measurement. matplotlib uses a non-interactive backend for chart generation. `demo.py` recreates its own demonstration database. The full benchmarks generate large CSV/database files in `generated_data`, which is ignored by Git; the generator and results are committed instead. Run B1 before the chatbot and B3 before the index experiment. Part A folders contain design documents and language-independent pseudocode, so they do not need an execution command.

## Task results

| Task | Result |
| --- | --- |
| A1 | Source-quality catalogue, SQLite schema, three question designs and scan/index comparison |
| A2 | Drop/duplicate/unit rules, min-max and z-score designs, formatting and fill/drop trade-offs |
| A3 | Four chart choices, daily summary schema and running-aggregation pseudocode |
| A4 | Debugging plan and reproducible perf_counter/timeit/cProfile methodology |
| A5 | Negation-aware lexicon, extractive summary and database-backed chatbot designs |
| B1 | 4 valid / 17 rejected small rows; 8,880 accepted monthly readings; SQL results; four charts; million-row cleaning comparison |
| B2 | Five malformed files rejected explicitly; quoted names safe with parameters; injection demonstrated only in a local fixture; insert and debug timings |
| B3 | Four methods agree at 8,760, 105,120 and 1,051,200 rows; raw timings, process RSS and profile saved |
| B4 | 50 complaints, 31/50 illustrative sentiment agreement, paired summaries, eight chatbot checks and measured index effects |

## Files and evidence

`SOLUTIONS.md` is the full report; `CSA08_Assignment5_Solution.pdf` is its PDF version with Python listings. `PART_A.md` and `PART_B.md` divide the report. Each TaskA folder has its own design; each TaskB folder contains code, inputs (or a generator), outputs and result explanations. All three `complete_code.py` files have matching captured output. `environment.json`, raw benchmark JSON and `profile.txt` retain measurement details. The SQLite database and charts use synthetic data, never live city observations. The downloadable ZIP includes the ready-made SQLite database. GitHub contains the CSVs and `TaskB1/demo.py` / `pipeline.py` that recreate it; the binary database is omitted there because of the upload tool size limit, as the assignment permits a database-creation script.

The B1 loop/pandas benchmark isolates three-column PM2.5 cleaning/normalisation; it is not a benchmark of every rule in the full pipeline. SQL query times exclude initial CSV loading, which is reported separately. RSS includes interpreter/library memory. The index improved a selective station query, but did not improve the slowest city-wide hourly query.

## Review and submission

The package includes programs and actual locally executed results. `output-image-*.png` files are labelled renderings of captured stdout, not terminal screenshots. The brief requires the student to execute the programs, understand the work and capture their own execution screenshots.

The 50 reference labels and salient sentences are illustrative judgements, not independently collected ground truth. Complete `TaskB4/personal_review.csv` after reading the complaints; then run:

```sh
python TaskB4/compare_personal_review.py
```

The detailed institutional pseudocode template was not attached; check the structured pseudocode against any template supplied separately. Share this repository with the course faculty and submit its link through the required course channel. Faculty sharing/course submission remains outstanding.
