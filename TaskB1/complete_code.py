import csv
import io
RAW = """station,date,pm25
Adyar,2026-10-01,48
Adyar,2026-10-02,NA
Adyar,2026-10-03,
Guindy,2026-10-01,95
Guindy,2026-10-02,-5
Guindy,2026-10-03,121"""
def load_clean(text):
    """Returns (station, date, pm25) tuples for valid, non-negative readings only."""
    rows = []
    for row in csv.DictReader(io.StringIO(text)):
        value = row['pm25'].strip()
        if value in ('', 'NA'):
            continue
        pm = float(value)
        if 0 <= pm <= 999:
            rows.append((row['station'],row['date'],pm))
    return rows

def min_max(values):
    if not values:
        return []
    low, high = min(values), max(values)
    if high == low:
        return [0.0]*len(values)
    return [round((v-low)/(high-low),3) for v in values]

clean = load_clean(RAW)
print(clean)
print(min_max([pm for _, _, pm in clean]))
# Additional check requested after the original program.
assert load_clean(RAW+'\nAdyar,2026-10-04,1000') == clean
print('Above-999 row skipped: PASS')
