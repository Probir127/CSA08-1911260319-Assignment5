"""Validated CSV -> SQLite pipeline; all demonstration data are synthetic."""
import csv
import json
import logging
import math
import sqlite3
import statistics
from datetime import date
from pathlib import Path

LOG = logging.getLogger(__name__)
STATIONS = ['Adyar', 'Guindy', 'Velachery', 'T Nagar', 'Anna Nagar',
            'Ambattur', 'Perambur', 'Royapuram', 'Mylapore',
            'Tambaram', 'Porur', "King's Park"]
UNITS = {s: ('F' if s in {'Guindy', 'Ambattur'} else 'C') for s in STATIONS}
LOOKUP = {' '.join(s.split()).casefold(): s for s in STATIONS}
FIELDS = ['station', 'date', 'hour', 'pm25', 'pm10', 'no', 'temperature', 'temp_unit']

class SourceError(ValueError):
    """A file cannot be interpreted under the declared source contract."""

def min_max(values):
    if not values:
        return []
    lo, hi = min(values), max(values)
    return [0.0 if hi == lo else (v-lo)/(hi-lo) for v in values]

def z_scores(values):
    if not values:
        return []
    mu = statistics.fmean(values)
    sigma = statistics.pstdev(values)
    return [0.0 if sigma == 0 else (v-mu)/sigma for v in values]

def number(text, label):
    if text is None or text.strip().casefold() in {'', 'na'}:
        raise ValueError(f'missing {label}')
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(f'non-finite {label}')
    return value

def clean_file(path):
    """Drop incomplete/invalid rows; retain first valid duplicate key."""
    accepted, issues, seen = [], [], set()
    try:
        with Path(path).open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream, strict=True)
            if reader.fieldnames != FIELDS:
                raise SourceError('expected exact comma-separated header: '+','.join(FIELDS))
            for raw in reader:
                line = reader.line_num
                try:
                    if None in raw or any(v is None for v in raw.values()):
                        raise ValueError('wrong number of columns')
                    station = LOOKUP.get(' '.join(raw['station'].split()).casefold())
                    if station is None:
                        raise ValueError('unknown or empty station')
                    day_text = raw['date'].strip()
                    day = date.fromisoformat(day_text).isoformat()
                    if day != day_text:
                        raise ValueError('date must be YYYY-MM-DD')
                    hour_text = raw['hour'].strip()
                    if not hour_text.isascii() or not hour_text.isdigit():
                        raise ValueError('hour must be an integer')
                    hour = int(hour_text)
                    if not 0 <= hour <= 23:
                        raise ValueError('hour outside 0..23')
                    pm25 = number(raw['pm25'], 'pm25')
                    pm10 = number(raw['pm10'], 'pm10')
                    no = number(raw['no'], 'no')
                    temperature = number(raw['temperature'], 'temperature')
                    unit = raw['temp_unit'].strip().upper()
                    if unit != UNITS[station]:
                        raise ValueError('temperature unit disagrees with station metadata')
                    if unit == 'F':
                        temperature = (temperature-32)*5/9
                    for label, value, upper in [('pm25',pm25,999), ('pm10',pm10,1999), ('no',no,999)]:
                        if not 0 <= value <= upper:
                            raise ValueError(f'{label} outside 0..{upper}')
                    if not -50 <= temperature <= 60:
                        raise ValueError('temperature outside -50..60 C')
                    key = (station, day, hour)
                    if key in seen:
                        raise ValueError('duplicate station/day/hour; first valid row retained')
                    seen.add(key)
                    accepted.append((station, day, hour, pm25, pm10, no, temperature))
                except (ValueError, OverflowError) as exc:
                    issues.append({'line':line, 'reason':str(exc), 'raw':raw})
        LOG.info('Accepted %d; rejected %d from %s',len(accepted),len(issues),path)
        return accepted, issues
    except (OSError, UnicodeError, csv.Error) as exc:
        raise SourceError(f'{type(exc).__name__}: {exc}') from exc

SCHEMA = """
CREATE TABLE stations (
    station TEXT PRIMARY KEY,
    temperature_unit TEXT NOT NULL CHECK (temperature_unit IN ('C','F'))
);
CREATE TABLE readings (
    station TEXT NOT NULL REFERENCES stations(station),
    day TEXT NOT NULL,
    hour INTEGER NOT NULL CHECK (hour BETWEEN 0 AND 23),
    pm25 REAL NOT NULL CHECK (pm25 BETWEEN 0 AND 999),
    pm10 REAL NOT NULL CHECK (pm10 BETWEEN 0 AND 1999),
    no REAL NOT NULL CHECK (no BETWEEN 0 AND 999),
    temperature_c REAL NOT NULL CHECK (temperature_c BETWEEN -50 AND 60),
    PRIMARY KEY (station, day, hour)
);
CREATE VIEW daily_summary AS
SELECT station, day, MIN(pm25) AS minimum, MAX(pm25) AS maximum,
       AVG(pm25) AS mean, COUNT(*) AS valid_count
FROM readings GROUP BY station, day;
"""

def store(rows, db):
    """Build a fresh demonstration DB; caller chooses its output path."""
    with sqlite3.connect(db) as con:
        con.execute('PRAGMA foreign_keys=ON')
        con.executescript('DROP VIEW IF EXISTS daily_summary; DROP TABLE IF EXISTS readings; DROP TABLE IF EXISTS stations;'+SCHEMA)
        con.executemany('INSERT INTO stations VALUES (?, ?)', UNITS.items())
        con.executemany('INSERT INTO readings VALUES (?, ?, ?, ?, ?, ?, ?)', rows)
        con.commit()

QUERIES = {
    'adyar_october_average': ("""SELECT AVG(pm25), COUNT(*) FROM readings
        WHERE station=? AND day>=? AND day<?""", ('Adyar','2026-10-01','2026-11-01')),
    'station_comparison': ("""SELECT station, AVG(pm25), COUNT(*) FROM readings
        WHERE day>=? AND day<? GROUP BY station ORDER BY AVG(pm25) DESC""", ('2026-10-01','2026-11-01')),
    'worst_hours': ("""SELECT hour, AVG(pm25), COUNT(*) FROM readings
        WHERE day>=? AND day<? GROUP BY hour ORDER BY AVG(pm25) DESC, hour LIMIT 5""", ('2026-10-01','2026-11-01')),
}

def queries(db):
    with sqlite3.connect(db) as con:
        return {name: con.execute(sql,params).fetchall() for name,(sql,params) in QUERIES.items()}

if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('input',type=Path)
    parser.add_argument('database',type=Path)
    args=parser.parse_args()
    rows, issues=clean_file(args.input)
    store(rows,args.database)
    print(json.dumps({'accepted':len(rows),'rejected':len(issues),'queries':queries(args.database)},indent=2))
