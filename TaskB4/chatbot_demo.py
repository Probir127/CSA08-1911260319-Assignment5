import json
from datetime import date
from pathlib import Path
from ai import chatbot,summarize,sentences
ROOT=Path(__file__).resolve().parent
DB=ROOT.parent/'TaskB1/air_quality.sqlite'
cases=[
 ('What is the PM2.5 in Adyar today?', 'Adyar on 2026-10-01:'),
 ("What is the PM2.5 in King's Park on 2026-10-01?", "King's Park on 2026-10-01:"),
 ('PM2.5 Adyar on 2026-11-05', 'No valid readings'),
 ('PM2.5 Adyar and Guindy today', 'Please specify exactly one'),
 ('PM2.5 Unknown today', 'Please specify exactly one'),
 ('PM2.5 Adyar on 2026-02-30', 'Invalid date'),
 ('Hello', 'Ask for PM2.5'),
 ('PM2.5 Adyar', 'Please specify today'),
]
answers=[]
for question,prefix in cases:
    answer=chatbot(question,DB,today=date(2026,10,1))
    assert answer.startswith(prefix)
    answers.append({'question':question,'answer':answer})
with __import__('sqlite3').connect(DB) as con:
    vals=[r[0] for r in con.execute('SELECT pm25 FROM readings WHERE station=? AND day=?',('Adyar','2026-10-01'))]
assert f'{sum(vals)/len(vals):.2f}' in answers[0]['answer']
text='Smoke covers the lane. The lane has smoke every night. Please inspect it.'
assert summarize(text) in sentences(text)
(ROOT/'chatbot_results.json').write_text(json.dumps({'clock_for_today':'2026-10-01 (fixed test date, not current readings)','cases':answers},indent=2))
print(json.dumps(answers,indent=2))
print('Eight chatbot cases and extractive-summary check: PASS')
