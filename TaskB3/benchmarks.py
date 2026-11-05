"""Reproducible benchmarks. Generated large files stay outside the submission."""
import argparse
import csv
import cProfile
import io
import json
import math
import os
import pstats
import resource
import sqlite3
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def rss_mib():
    raw=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return raw/(1024*1024 if sys.platform=='darwin' else 1024)

def clean_loops(path):
    values=[]
    with open(path,newline='') as f:
        for row in csv.DictReader(f):
            text=row['pm25']
            if text in ('','NA'):
                continue
            value=float(text)
            if math.isfinite(value) and 0<=value<=999:
                values.append(value)
    lo,hi=min(values),max(values)
    normalized=[0.0 if lo==hi else (x-lo)/(hi-lo) for x in values]
    return len(values),sum(values),sum(normalized)

def clean_pandas(path):
    import pandas as pd
    df=pd.read_csv(path,keep_default_na=False)
    df['pm25']=pd.to_numeric(df.pm25.replace({'NA':None,'':None}),errors='coerce')
    df=df.dropna(subset=['pm25'])
    df=df[df.pm25.between(0,999)].copy()
    lo,hi=df.pm25.min(),df.pm25.max()
    df['normalized']=0.0 if lo==hi else (df.pm25-lo)/(hi-lo)
    return len(df),float(df.pm25.sum()),float(df.normalized.sum())

def mean_lists(path):
    groups=defaultdict(list)
    with open(path,newline='') as f:
        for row in csv.DictReader(f):
            groups[(row['station'],row['day'])].append(float(row['pm25']))
    return {key:statistics.mean(values) for key,values in groups.items()}

def mean_running(path):
    groups={}
    with open(path,newline='') as f:
        for row in csv.DictReader(f):
            key=(row['station'],row['day'])
            if key not in groups: groups[key]=[0.0,0]
            groups[key][0]+=float(row['pm25']);groups[key][1]+=1
    return {key:total/count for key,(total,count) in groups.items()}

def mean_pandas(path):
    import pandas as pd
    frame=pd.read_csv(path)
    return frame.groupby(['station','day']).pm25.mean().to_dict()

def load_database(path,db):
    with sqlite3.connect(db) as con:
        con.execute('DROP TABLE IF EXISTS aq')
        con.execute('CREATE TABLE aq (station TEXT, day TEXT, hour INTEGER, pm25 REAL)')
        with open(path,newline='') as f:
            con.executemany('INSERT INTO aq VALUES (?,?,?,?)',
                ((r['station'],r['day'],int(r['hour']),float(r['pm25'])) for r in csv.DictReader(f)))
        con.commit()

def mean_sql(db):
    with sqlite3.connect(db) as con:
        return {(s,d):m for s,d,m in con.execute('SELECT station,day,AVG(pm25) FROM aq GROUP BY station,day')}

def same(a,b):
    assert a.keys()==b.keys()
    assert all(math.isclose(a[k],b[k],rel_tol=1e-10,abs_tol=1e-9) for k in a)

def worker(kind,path):
    # Imports excluded from timing; RSS includes interpreter/import overhead.
    if 'pandas' in kind:
        import pandas
    fn={'clean_loops':clean_loops,'clean_pandas':clean_pandas,
        'lists':mean_lists,'running':mean_running,'pandas':mean_pandas,'sql':mean_sql}[kind]
    start=time.perf_counter();out=fn(path);elapsed=time.perf_counter()-start
    if isinstance(out,dict):
        # Every output group is validated, not just a summary checksum.
        for (station,day),value in out.items():
            si=int(station[1:])-1;di=(date.fromisoformat(day)-date(2026,1,1)).days
            expected=20+si+(di%31)+11.5/10
            assert math.isclose(value,expected,rel_tol=1e-10,abs_tol=1e-9)
        check={'groups':len(out),'sum_means':sum(out.values())}
    else:
        check={'valid_rows':out[0],'sum_pm25':out[1],'sum_normalized':out[2]}
    return {'seconds':elapsed,'process_peak_rss_mib':rss_mib(),'check':check}

def samples(kind,path):
    runs=[]
    for _ in range(3):
        result=subprocess.run([sys.executable,__file__,'--worker',kind,str(path)],text=True,capture_output=True,check=True)
        runs.append(json.loads(result.stdout))
    return {'runs':runs,'median_seconds':statistics.median(r['seconds'] for r in runs),
            'max_peak_rss_mib':max(r['process_peak_rss_mib'] for r in runs)}

def main(work):
    work.mkdir(parents=True,exist_ok=True)
    b1=[]
    for n in [1000,100000,1000000]:
        path=work/f'clean_{n}.csv'
        valid=[]
        with path.open('w',newline='') as f:
            w=csv.writer(f);w.writerow(['station','day','pm25'])
            for i in range(n):
                v='NA' if i%10==0 else '' if i%10==1 else -5 if i%10==2 else 1000 if i%10==3 else i%500
                w.writerow(['Adyar','2026-10-01',v])
                if isinstance(v,int) and 0<=v<=999:valid.append(v)
        lo,hi=min(valid),max(valid)
        expected=[len(valid),sum(valid),sum((v-lo)/(hi-lo) for v in valid)]
        # Data repeat every 500 rows; first 1,000 contain the full range.
        methods={name:samples(name,path) for name in ['clean_loops','clean_pandas']}
        for method in methods.values():
            for run in method['runs']:
                check=list(run['check'].values())
                assert all(math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-8) for a,b in zip(check,expected))
        b1.append({'rows':n,'methods':methods})
        print(f'Cleaning {n}: '+str({k:round(v['median_seconds'],4) for k,v in methods.items()}),flush=True)
    (ROOT.parent/'TaskB1/cleaning_benchmarks.json').write_text(json.dumps(b1,indent=2))
    b3=[]
    for stations in [1,12,120]:
        path=work/f'year_{stations}.csv';db=work/f'year_{stations}.sqlite'
        with path.open('w',newline='') as f:
            w=csv.writer(f);w.writerow(['station','day','hour','pm25'])
            for si in range(stations):
                for di in range(365):
                    for hour in range(24):
                        w.writerow([f'S{si+1:03}',(date(2026,1,1)+timedelta(days=di)).isoformat(),hour,round(20+si+di%31+hour/10,1)])
        start=time.perf_counter();load_database(path,db);load_seconds=time.perf_counter()-start
        methods={name:samples(name,db if name=='sql' else path) for name in ['lists','running','pandas','sql']}
        for method in methods.values():
            for run in method['runs']:assert run['check']['groups']==stations*365
        if stations==1:
            reference=mean_lists(path)
            for fn,arg in [(mean_running,path),(mean_pandas,path),(mean_sql,db)]:same(reference,fn(arg))
        b3.append({'stations':stations,'rows':stations*8760,'sql_load_seconds':load_seconds,'methods':methods})
        print(f'Year {stations} stations: '+str({k:round(v['median_seconds'],4) for k,v in methods.items()}),flush=True)
    (ROOT/'measurements.json').write_text(json.dumps(b3,indent=2))
    profile=cProfile.Profile();profile.runcall(mean_lists,work/'year_120.csv')
    stream=io.StringIO();pstats.Stats(profile,stream=stream).strip_dirs().sort_stats('cumulative').print_stats(30)
    stream.write('\nSORTED BY INTERNAL TIME\n');pstats.Stats(profile,stream=stream).strip_dirs().sort_stats('tottime').print_stats(20)
    (ROOT/'profile.txt').write_text(stream.getvalue())
    print('All four methods agree with independently calculated means at all three sizes. Profile saved.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--work-dir',type=Path);parser.add_argument('--worker',nargs=2)
    args=parser.parse_args()
    if args.worker:print(json.dumps(worker(*args.worker)))
    elif args.work_dir:main(args.work_dir)
    else:parser.error('--work-dir is required for a benchmark run')
