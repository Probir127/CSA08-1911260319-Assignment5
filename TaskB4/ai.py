"""Transparent teaching baselines; not a validated public-service AI system."""
import re
import sqlite3
from collections import Counter
from datetime import date
POSITIVE={'good','clean','fast','helpful','improved'}
NEGATIVE={'bad','dirty','slow','rude','smoke','broken'}
NEGATORS={'not','never','no'}
STOP=set('a an the and or but is are was were be been being i we you they it this that to of in on at for from with as my our your has have had do does did please very there near every now today yesterday still also'.split())

def words(text):
    return re.findall(r"[a-z]+(?:'[a-z]+)?",text.lower())

def sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+',text.strip()) if s.strip()]

def score(text):
    total=0
    for sentence in sentences(text):
        tokens=words(sentence)
        for i,word in enumerate(tokens):
            value=1 if word in POSITIVE else -1 if word in NEGATIVE else 0
            if i and tokens[i-1] in NEGATORS:value=-value
            total+=value
    return total

def label(text):
    value=score(text)
    return 'positive' if value>0 else 'negative' if value<0 else 'neutral'

def summary_indices(text,k=1):
    parts=sentences(text)
    if k<=0:return []
    token_lists=[[w for w in words(s) if w not in STOP] for s in parts]
    counts=Counter(w for tokens in token_lists for w in tokens)
    # Average frequency avoids rewarding a sentence only for being long.
    scores=[sum(counts[w] for w in tokens)/len(tokens) if tokens else 0 for tokens in token_lists]
    selected=sorted(range(len(parts)),key=lambda i:(-scores[i],i))[:k]
    return sorted(selected)

def summarize(text,k=1):
    parts=sentences(text)
    return ' '.join(parts[i] for i in summary_indices(text,k))

def first_k(text,k=1):
    return ' '.join(sentences(text)[:max(0,k)])

def chatbot(question,db,today=None):
    q=' '.join(question.lower().split())
    if 'pm2.5' not in q and 'pm25' not in q:
        return 'Ask for PM2.5, a station name, and today or a YYYY-MM-DD date.'
    with sqlite3.connect(db) as con:
        stations=[r[0] for r in con.execute('SELECT station FROM stations')]
        matched=[s for s in stations if re.search(r'(?<!\w)'+re.escape(s.lower())+r'(?!\w)',q)]
        if len(matched)!=1:return 'Please specify exactly one known station.'
        literal=re.findall(r'\b\d{4}-\d{2}-\d{2}\b',q)
        if len(literal)>1:return 'Please specify one date.'
        if literal:
            try:day=date.fromisoformat(literal[0]).isoformat()
            except ValueError:return 'Invalid date; use YYYY-MM-DD.'
        elif 'today' in words(q):day=(today or date.today()).isoformat()
        else:return 'Please specify today or a YYYY-MM-DD date.'
        mean,count=con.execute('SELECT AVG(pm25),COUNT(*) FROM readings WHERE station=? AND day=?',(matched[0],day)).fetchone()
    if not count:return f'No valid readings for {matched[0]} on {day}.'
    return f'{matched[0]} on {day}: mean PM2.5 {mean:.2f} micrograms/m3 from {count} valid readings.'
