import csv
import json
import math
import statistics
from pathlib import Path
from pipeline import FIELDS, STATIONS, UNITS, clean_file, min_max, z_scores, store, queries
ROOT=Path(__file__).resolve().parent

def write_csv(path, rows):
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(FIELDS);w.writerows(rows)

def main():
    base=['Adyar','2026-10-01',0,48,80,15,30,'C']
    rows=[base, ['  aDyAr  ','2026-10-01',1,60,90,20,31,' c '],
          ['Guindy','2026-10-01',0,95,150,25,86,'F'],
          ["King's Park",'2026-10-01',0,40,70,10,29,'C']]
    # Each row independently illustrates one declared quality problem.
    changes=[(3,''),(4,'NA'),(5,-1),(3,1000),(3,'broken'),(3,'nan'),
             (3,'inf'),(6,61),(1,'2026-02-30'),(1,'01/10/2026'),
             (2,24),(2,'1.5'),(0,'Unknown'),(7,'F')]
    for index,value in changes:
        row=base.copy();row[index]=value;rows.append(row)
    rows.extend([base,base[:-1],base+['extra']])
    write_csv(ROOT/'small_messy.csv',rows)
    clean,issues=clean_file(ROOT/'small_messy.csv')
    assert len(clean)==4 and len(issues)==17
    assert clean[1][:3]==('Adyar','2026-10-01',1)
    assert clean[2][-1]==30.0
    assert min_max([5,5])==[0,0] and z_scores([5,5])==[0,0]
    assert min_max([])==[] and z_scores([])==[]
    assert min_max([48,60,95,40])==[(x-40)/55 for x in [48,60,95,40]]
    assert abs(statistics.fmean(z_scores([48,60,95,40])))<1e-12
    (ROOT/'small_before_after.json').write_text(json.dumps({'raw_rows':rows,'clean_rows':clean,'issues':issues,'pm25_minmax':min_max([r[3] for r in clean]),'pm25_zscore':z_scores([r[3] for r in clean])},indent=2))
    with (ROOT/'small_cleaned.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['station','day','hour','pm25','pm10','no','temperature_c']);w.writerows(clean)
    monthly=[]
    for i,station in enumerate(STATIONS):
        for day in range(1,32):
            for hour in range(24):
                pm=round(25+i*3+0.7*day+(18 if hour in {7,8,9,18,19,20} else 0)+4*math.sin(day),2)
                temp=round(25+5*math.sin((hour-6)*math.pi/12)+0.05*day,2)
                reading=[station,f'2026-10-{day:02}',hour,pm,round(pm*1.5,2),round(10+i+hour/5,2),round(temp*9/5+32,2) if UNITS[station]=='F' else temp,UNITS[station]]
                if (day*24+hour+i)%173==0: reading[3]='NA'
                monthly.append(reading)
    write_csv(ROOT/'october_synthetic.csv',monthly)
    clean,issues=clean_file(ROOT/'october_synthetic.csv')
    store(clean,ROOT/'air_quality.sqlite')
    result=queries(ROOT/'air_quality.sqlite')
    (ROOT/'query_results.json').write_text(json.dumps(result,indent=2))
    (ROOT/'monthly_audit.json').write_text(json.dumps({'input_rows':len(monthly),'accepted':len(clean),'rejected':len(issues),'issues':issues},indent=2))
    import sqlite3
    import pandas as pd
    import os, tempfile
    os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir())/"csa08-mpl"))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    with sqlite3.connect(ROOT/'air_quality.sqlite') as con:
        daily=pd.read_sql_query('SELECT * FROM daily_summary ORDER BY station,day',con)
        frame=pd.read_sql_query('SELECT * FROM readings',con)
    daily.to_csv(ROOT/'daily_summary.csv',index=False,float_format='%.4f')
    plt.rcParams.update({'font.size':10,'figure.dpi':130})
    def save(name):
        plt.tight_layout();plt.savefig(ROOT/name,dpi=180);plt.close()
    fig,ax=plt.subplots(figsize=(8.2,4))
    for station in ['Adyar','Guindy']:
        d=daily[daily.station==station];ax.plot(pd.to_datetime(d.day),d['mean'],label=station)
    ax.set(title='Synthetic October 2026 - daily PM2.5 trend',xlabel='Date',ylabel='Mean PM2.5 (micrograms/m3)');ax.legend();fig.autofmt_xdate();save('trend.png')
    fig,ax=plt.subplots(figsize=(8.2,4.5))
    frame.groupby('station').pm25.mean().sort_values().plot.barh(ax=ax,color='#1c7293')
    ax.set(title='Synthetic October 2026 - station comparison',xlabel='Mean PM2.5 (micrograms/m3)',ylabel='Station');save('stations.png')
    fig,ax=plt.subplots(figsize=(8.2,4))
    d=frame[frame.station=='Adyar'];ax.scatter(d.temperature_c,d.pm25,s=8,alpha=.35)
    ax.set(title='Synthetic Adyar - temperature and PM2.5',xlabel='Temperature (degrees C)',ylabel='PM2.5 (micrograms/m3)');save('scatter.png')
    fig,ax=plt.subplots(figsize=(8.2,4))
    ax.boxplot([frame[frame.hour==h].pm25.to_numpy() for h in range(24)],tick_labels=list(range(24)),showfliers=False)
    ax.set(title='Synthetic October 2026 - PM2.5 by hour',xlabel='Hour (local, 0-23)',ylabel='PM2.5 (micrograms/m3)');save('hours.png')
    print('Small-file validation: 4 accepted, 17 rejected; canonical names/Fahrenheit/normalisation PASS')
    print(f'Month: {len(monthly)} input; {len(clean)} accepted; {len(issues)} rejected')
    print(json.dumps(result,indent=2))
    print('Four charts and daily_summary.csv generated; data are synthetic.')
if __name__=='__main__': main()
