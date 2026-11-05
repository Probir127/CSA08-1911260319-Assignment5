"""Controlled before/after index trial on B3's initially unindexed table."""
import argparse
import json
import shutil
import sqlite3
import statistics
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
QUERIES={
 'station_month':('SELECT AVG(pm25) FROM aq WHERE station=? AND day>=? AND day<?',('S001','2026-10-01','2026-11-01')),
 'station_comparison':('SELECT station,AVG(pm25) FROM aq WHERE day>=? AND day<? GROUP BY station ORDER BY AVG(pm25) DESC',('2026-10-01','2026-11-01')),
 'worst_hours':('SELECT hour,AVG(pm25) FROM aq WHERE day>=? AND day<? GROUP BY hour ORDER BY AVG(pm25) DESC LIMIT 5',('2026-10-01','2026-11-01')),
}
def measure(con):
    result={}
    for name,(sql,args) in QUERIES.items():
        con.execute(sql,args).fetchall() # warm-up, not timed
        runs=[]
        for _ in range(7):
            start=time.perf_counter();rows=con.execute(sql,args).fetchall();runs.append(time.perf_counter()-start)
        result[name]={'runs_seconds':runs,'median_seconds':statistics.median(runs),'result':rows,
                     'plan':con.execute('EXPLAIN QUERY PLAN '+sql,args).fetchall()}
    return result

def main(source):
    dest=source.with_name('index_experiment.sqlite');shutil.copy2(source,dest)
    with sqlite3.connect(dest) as con:
        before=measure(con)
        slowest=max(before,key=lambda k:before[k]['median_seconds'])
        start=time.perf_counter();con.execute('CREATE INDEX idx_station_day ON aq(station,day)');con.commit();build=time.perf_counter()-start
        after=measure(con)
        for name in before:
            # Equal query results, allowing harmless changes in summation order.
            a,b=before[name]['result'],after[name]['result']
            assert len(a)==len(b)
            for x,y in zip(a,b):
                for u,v in zip(x,y):
                    if isinstance(u,float):assert abs(u-v)<1e-8
                    else:assert u==v
    result={'rows':1051200,'repetitions':7,'baseline_slowest':slowest,'index_build_seconds':build,
            'before':before,'after':after,'note':'B3 heap table. B1 already has a composite primary-key index with this prefix; do not add a redundant production index.'}
    (ROOT/'index_results.json').write_text(json.dumps(result,indent=2))
    print('Baseline slowest query:',slowest)
    for name in before:
        print(f"{name}: {before[name]['median_seconds']:.6f}s -> {after[name]['median_seconds']:.6f}s; ratio {before[name]['median_seconds']/after[name]['median_seconds']:.2f}x")
    print(f'Index construction: {build:.6f}s')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('database',type=Path);main(p.parse_args().database)
