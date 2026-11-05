import csv
import io
import json
import logging
import sqlite3
import statistics
import sys
import time
import timeit
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'TaskB1'))
sys.path.insert(0,str(ROOT.parent/'TaskB4'))
from pipeline import FIELDS, SourceError,clean_file
from ai import label

def main():
    inputs=ROOT/'inputs';inputs.mkdir(exist_ok=True)
    header=','.join(FIELDS)
    (inputs/'missing_column.csv').write_text('station,date,hour,pm25\nAdyar,2026-10-01,0,48\n')
    (inputs/'wrong_delimiter.csv').write_text(header.replace(',',';')+'\nAdyar;2026-10-01;0;48;80;15;30;C\n')
    (inputs/'empty.csv').write_text('')
    (inputs/'latin1.csv').write_bytes((header+'\nAdyár,2026-10-01,0,48,80,15,30,C\n').encode('latin-1'))
    (inputs/'unclosed_quote.csv').write_text(header+'\n"Adyar,2026-10-01,0,48,80,15,30,C\n')
    cases=[]
    for p in sorted(inputs.glob('*.csv')):
        try:clean_file(p)
        except SourceError as exc:cases.append({'file':p.name,'outcome':type(exc).__name__,'message':str(exc)})
        else:raise AssertionError(f'Expected rejection: {p.name}')
    con=sqlite3.connect(':memory:')
    con.execute('CREATE TABLE aq(station TEXT,pm25 REAL)')
    con.executemany('INSERT INTO aq VALUES (?,?)',[('Adyar',48),('Guindy',95),("King's Park",40)])
    sql=[]
    for name in ["King's Park","Adyar' OR '1'='1"]:
        unsafe="SELECT AVG(pm25) FROM aq WHERE station='"+name+"'"
        try:out=con.execute(unsafe).fetchone()[0]
        except sqlite3.Error as exc:out=type(exc).__name__+': '+str(exc)
        safe=con.execute('SELECT AVG(pm25) FROM aq WHERE station=?',(name,)).fetchone()[0]
        sql.append({'input':name,'unsafe_query':unsafe,'unsafe_result':out,'parameterized_result':safe})
    assert sql[0]['parameterized_result']==40
    assert isinstance(sql[0]['unsafe_result'],str)
    assert abs(sql[1]['unsafe_result']-61)<1e-12 and sql[1]['parameterized_result'] is None
    con.close()
    timings={}
    data=[('Adyar',float(i%500)) for i in range(100000)]
    for method in ['execute_loop','executemany']:
        runs=[]
        for _ in range(5):
            with sqlite3.connect(':memory:') as con:
                con.execute('CREATE TABLE aq(station TEXT,pm25 REAL)')
                start=time.perf_counter()
                if method=='execute_loop':
                    for row in data:con.execute('INSERT INTO aq VALUES (?,?)',row)
                else:con.executemany('INSERT INTO aq VALUES (?,?)',data)
                con.commit();runs.append(time.perf_counter()-start)
                assert con.execute('SELECT COUNT(*),SUM(pm25) FROM aq').fetchone()==(100000,24950000)
        timings[method]={'runs_seconds':runs,'median_seconds':statistics.median(runs)}
    probes=[('Good, another smoke-filled evening.','negative'),('The road is not not clean.','positive'),
            ('Clean park, dirty road.','neutral'),('Helpful staff, broken sensor; overall dissatisfied.','negative')]
    sentiment=[{'text':t,'reference':ref,'actual':label(t),'agrees':ref==label(t)} for t,ref in probes]
    logger=logging.getLogger('experiment');logger.propagate=False
    stream=io.StringIO();logger.handlers[:]=[logging.StreamHandler(stream)]
    # Buffered output excludes terminal rendering. Exactly 10,000 calls per trial.
    debug={}
    for method in ['print_buffered','logging_disabled','logging_enabled']:
        runs=[]
        for _ in range(3):
            buffer=io.StringIO();stream.seek(0);stream.truncate(0)
            logger.setLevel(logging.WARNING if method=='logging_disabled' else logging.DEBUG)
            action=(lambda:print('row',42,file=buffer)) if method=='print_buffered' else (lambda:logger.debug('row %s',42))
            runs.append(timeit.timeit(action,number=10000))
        debug[method]={'runs_seconds':runs,'median_seconds':statistics.median(runs)}
    evidence={'files':cases,'sql':sql,'insert_100000_rows_one_transaction':timings,'sentiment':sentiment,'debug_10000_calls':debug}
    (ROOT/'evidence.json').write_text(json.dumps(evidence,indent=2))
    print(json.dumps(evidence,indent=2))
    print('Adversarial checks and insertion equivalence: PASS')
if __name__=='__main__':main()
