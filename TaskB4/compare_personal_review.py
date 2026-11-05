"""Calculate actual student agreement only after all review fields are filled."""
import csv
import json
from pathlib import Path
from ai import label,sentences,summary_indices
ROOT=Path(__file__).resolve().parent

def main():
    with (ROOT/'personal_review.csv').open(newline='',encoding='utf-8') as f:
        rows=list(csv.DictReader(f))
    original=json.loads((ROOT/'complaints.json').read_text())
    expected={str(r['id']):r['text'] for r in original}
    seen=set();review=[]
    for row in rows:
        ident=row['id']
        if ident not in expected or ident in seen or row['complaint']!=expected[ident]:
            raise ValueError('Review IDs/text must match the original 50 complaints exactly.')
        seen.add(ident)
        sentiment=row['my_sentiment'].strip().lower()
        if sentiment not in {'positive','negative','neutral'}:
            raise ValueError(f'Complaint {ident}: enter your own positive/negative/neutral label.')
        try:idx=int(row['my_salient_sentence_number'])-1
        except ValueError as exc:raise ValueError(f'Complaint {ident}: enter your chosen one-based sentence number.') from exc
        if not 0<=idx<len(sentences(row['complaint'])):
            raise ValueError(f'Complaint {ident}: invalid sentence number.')
        review.append((label(row['complaint'])==sentiment,idx in summary_indices(row['complaint']),idx==0))
    if seen!=expected.keys():raise ValueError('Complete all 50 complaints.')
    print(json.dumps({'reviewed':len(review),'sentiment_agreement':sum(r[0] for r in review),
                      'frequency_salience_matches':sum(r[1] for r in review),
                      'first_sentence_salience_matches':sum(r[2] for r in review)},indent=2))
if __name__=='__main__':main()
