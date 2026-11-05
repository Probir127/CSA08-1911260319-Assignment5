"""Focused regression and saved-evidence checks; run after the task scripts."""
import csv
import json
import math
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'TaskB1'))
sys.path.insert(0,str(ROOT/'TaskB4'))
from pipeline import clean_file, min_max, z_scores, FIELDS, SourceError, store
from ai import label,summarize,chatbot

class AssignmentChecks(unittest.TestCase):
    def test_original_exercises(self):
        expected={
            'TaskB1':"[('Adyar', '2026-10-01', 48.0), ('Guindy', '2026-10-01', 95.0), ('Guindy', '2026-10-03', 121.0)]\n[0.0, 0.644, 1.0]\nAbove-999 row skipped: PASS\n",
            'TaskB2':'54.0 108.0\nNone\n',
            'TaskB4':'positive | Roads are clean and the bus was fast.\nnegative | Smoke from the factory, air is bad.\nnegative | The staff were not helpful.\npositive | Not bad, service improved.\n'}
        for task,output in expected.items():
            with self.subTest(task=task):
                result=subprocess.run([sys.executable,str(ROOT/task/'complete_code.py')],text=True,capture_output=True,check=True)
                self.assertEqual(result.stdout,output)

    def test_cleaned_fixture_and_scaling(self):
        rows,issues=clean_file(ROOT/'TaskB1/small_messy.csv')
        self.assertEqual(len(rows),4);self.assertEqual(len(issues),17)
        self.assertEqual(rows[2],('Guindy','2026-10-01',0,95.,150.,25.,30.))
        self.assertEqual(min_max([4,6,8]),[0,0.5,1])
        zs=z_scores([4,6,8])
        self.assertAlmostEqual(sum(zs),0)
        self.assertAlmostEqual(sum(z*z for z in zs)/3,1)
        for fn in [min_max,z_scores]:
            self.assertEqual(fn([]),[]);self.assertEqual(fn([7,7]),[0,0])

    def test_invalid_row_does_not_reserve_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'data.csv'
            with p.open('w',encoding='utf-8-sig',newline='') as f:
                w=csv.writer(f);w.writerow(FIELDS)
                w.writerows([['Adyar','2026-10-01',0,-1,80,10,30,'C'],
                             ['Adyar','2026-10-01',0,50,80,10,30,'C'],
                             ['Adyar','2026-10-01',0,99,80,10,30,'C']])
            rows,issues=clean_file(p)
            self.assertEqual(len(rows),1);self.assertEqual(rows[0][3],50)
            self.assertEqual(len(issues),2)

    def test_corrupt_files_fail_explicitly(self):
        for p in (ROOT/'TaskB2/inputs').glob('*.csv'):
            with self.subTest(file=p.name),self.assertRaises(SourceError):clean_file(p)

    def test_database_constraints_and_independent_averages(self):
        rows,_=clean_file(ROOT/'TaskB1/small_messy.csv')
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/'small.sqlite';store(rows,db)
            with sqlite3.connect(db) as con:
                self.assertEqual(con.execute("SELECT AVG(pm25),COUNT(*) FROM readings WHERE station='Adyar'").fetchone(),(54.0,2))
                self.assertEqual(con.execute("SELECT minimum,maximum,mean,valid_count FROM daily_summary WHERE station='Adyar'").fetchone(),(48.0,60.0,54.0,2))
                with self.assertRaises(sqlite3.IntegrityError):con.execute('INSERT INTO readings VALUES (?,?,?,?,?,?,?)',rows[0])
                con.execute('PRAGMA foreign_keys=ON')
        with sqlite3.connect(ROOT/'TaskB1/air_quality.sqlite') as con:
            self.assertEqual(con.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(con.execute('SELECT COUNT(*) FROM readings').fetchone()[0],8880)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM daily_summary').fetchone()[0],372)

    def test_saved_benchmark_evidence(self):
        for filename,counts in [('TaskB1/cleaning_benchmarks.json',[1000,100000,1000000]),('TaskB3/measurements.json',[8760,105120,1051200])]:
            data=json.loads((ROOT/filename).read_text())
            self.assertEqual([r['rows'] for r in data],counts)
            for size in data:
                checks=[]
                for method in size['methods'].values():
                    self.assertEqual(len(method['runs']),3)
                    for run in method['runs']:
                        self.assertGreater(run['seconds'],0)
                        checks.append(run['check'])
                for check in checks:
                    for key in checks[0]:self.assertTrue(math.isclose(check[key],checks[0][key],rel_tol=1e-9,abs_tol=1e-7))

    def test_ai_expected_scope_and_personal_review(self):
        self.assertEqual(label('not good'),'negative');self.assertEqual(label('not bad'),'positive')
        self.assertEqual(summarize(''), '')
        text='Smoke fills the lane. Smoke enters the lane every evening. Please inspect it.'
        self.assertIn(summarize(text),text)
        result=subprocess.run([sys.executable,str(ROOT/'TaskB4/compare_personal_review.py')],text=True,capture_output=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('enter your own',result.stderr)
        evidence=json.loads((ROOT/'TaskB4/evaluation.json').read_text())
        self.assertEqual(evidence['complaints'],50)
        self.assertEqual(evidence['label_agreement'],31)

    def test_chatbot_no_data_and_invalid_dates(self):
        db=ROOT/'TaskB1/air_quality.sqlite'
        self.assertTrue(chatbot('PM2.5 Adyar 2026-11-05',db).startswith('No valid readings'))
        self.assertTrue(chatbot('PM2.5 Adyar 2026-02-30',db).startswith('Invalid date'))
        self.assertTrue(chatbot("PM2.5 King's Park 2026-10-01",db).startswith("King's Park on 2026-10-01:"))

if __name__=='__main__':unittest.main(verbosity=2)
