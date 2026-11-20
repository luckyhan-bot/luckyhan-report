"""주말 다시보기 준비: 그 주(월~금) 매일 정리에서 밀린 리포트 후보 모으기 + PDF 텍스트 받기.
사용: python3 scripts/weekly.py <토요일 YYYY-MM-DD>
출력: work/weekly/<토요일>/candidates.json, work/weekly/<토요일>/pdf/<id>.txt
"""
import json, os, sys, glob, datetime, subprocess
sat = datetime.date.fromisoformat(sys.argv[1])
mon = sat - datetime.timedelta(days=sat.weekday())          # 그 주 월요일
days = [(mon + datetime.timedelta(days=i)).isoformat() for i in range(5)]
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
W = os.path.join(ROOT, 'work', 'weekly', sat.isoformat()); os.makedirs(os.path.join(W, 'pdf'), exist_ok=True)

pool, have = [], []
for d in days:
    f = os.path.join(ROOT, 'data', 'pool', f'{d}.json')
    if os.path.exists(f):
        have.append(d); pool += json.load(open(f, encoding='utf-8'))['reports']
picked_codes = {r['code'] for r in pool if r['picked']}
# 그 주에 한 번이라도 뽑힌 종목은 제외, 종목당 리포트 하나(목표가 변경 > 상승여력)
best = {}
for r in pool:
    if r['picked'] or r['code'] in picked_codes:
        continue
    k = (r['targetDir'] in ('up', 'down'), r['targetDir'] == 'up', r['upside'] or -999)
    if r['code'] not in best or k > best[r['code']][0]:
        best[r['code']] = (k, r)
cands = sorted((v[1] for v in best.values()), key=lambda r: (r['date'], -(r['mcap'] or 0)))

for r in cands:
    if not r.get('pdf'):
        continue
    pdf, txt = os.path.join(W, 'pdf', f"{r['id']}.pdf"), os.path.join(W, 'pdf', f"{r['id']}.txt")
    try:
        if not os.path.exists(pdf):
            from urllib.parse import urlparse
            u = urlparse(r['pdf'])
            subprocess.run(['curl', '-sS', '-L', '-A', 'Mozilla/5.0', '-e', f'{u.scheme}://{u.netloc}/', '-o', pdf, r['pdf']], timeout=60, check=True)
        subprocess.run(['pdftotext', '-layout', pdf, txt], timeout=60, check=True)
        r['textFile'] = os.path.relpath(txt, ROOT)
    except Exception:
        r['textFile'] = None

json.dump({'saturday': sat.isoformat(), 'range': [days[0], days[-1]], 'daysWithData': have, 'candidates': cands},
          open(os.path.join(W, 'candidates.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"{days[0]}~{days[-1]} | 정리된 날 {len(have)}일 {have} | 밀린 후보 {len(cands)}개")
for r in cands:
    dir_ = {'up': '▲', 'down': '▼', 'keep': '=', 'new': '★'}.get(r['targetDir'], '')
    print(f"  {r['id']} {r['date'][5:]} {r['name']}({r['code']}) {r['broker']} | {r['opinion']} {r['target'] or '-'} {dir_} | 상승여력 {r['upside']} | {r['sector']}>{r['sub']} | 밀린 이유: {r['reason']}")
