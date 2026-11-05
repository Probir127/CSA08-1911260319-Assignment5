import json
import statistics
import time
from pathlib import Path
from ai import label,score,sentences,summary_indices,summarize,first_k
ROOT=Path(__file__).resolve().parent

def main():
    rows=json.loads((ROOT/'complaints.json').read_text())
    assert len(rows)>=50
    assert label('not good')=='negative' and label('not bad')=='positive'
    assert summarize('',1)=='' and summarize('One sentence.',0)==''
    results=[]
    for r in rows:
        indices=summary_indices(r['text'])
        results.append({**r,'score':score(r['text']),'predicted_label':label(r['text']),
            'label_agrees':label(r['text'])==r['reference_label'],
            'frequency_summary':summarize(r['text']), 'first_sentence_summary':first_k(r['text']),
            'frequency_matches_reference':r['reference_salient_sentence'] in indices,
            'first_matches_reference':r['reference_salient_sentence']==0})
    timing={}
    for name,fn in [('sentiment',label),('frequency_summary',summarize),('first_sentence',first_k)]:
        runs=[]
        for _ in range(5):
            start=time.perf_counter()
            for r in rows:fn(r['text'])
            runs.append(time.perf_counter()-start)
        timing[name]={'runs_seconds':runs,'median_seconds_for_50':statistics.median(runs)}
    evidence={'complaints':len(rows),'label_agreement':sum(r['label_agrees'] for r in results),
              'frequency_salience_matches':sum(r['frequency_matches_reference'] for r in results),
              'first_sentence_salience_matches':sum(r['first_matches_reference'] for r in results),
              'reference_note':'Illustrative reference labels; not independently validated ground truth.',
              'timings':timing,'results':results}
    (ROOT/'evaluation.json').write_text(json.dumps(evidence,indent=2))
    print(json.dumps({k:v for k,v in evidence.items() if k!='results'},indent=2))
    print('Known failures:')
    for r in results:
        if not r['label_agrees']:print(f"{r['id']:02}: reference={r['reference_label']}, predicted={r['predicted_label']} | {r['text']}")
if __name__=='__main__':main()
