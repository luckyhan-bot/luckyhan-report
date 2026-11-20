"""주말 다시보기 → data/<토요일>.json (type: weekly), data/index.json 갱신.
사용: python3 scripts/build_weekly.py <토요일>
work/weekly/<토요일>/content.json (Claude가 PDF를 읽고 직접 다시 쓴 문장)
{
  "headline": ["첫 줄", "둘째 줄(빨강)"], "dek": "소개 1~2문장",
  "picks": {"<리포트 id>": {"pushed": "왜 밀렸나(그 주 정리에서 빠진 이유를 쉬운 말로)",
                           "chosen": "왜 골랐나(지금 읽어볼 가치)",
                           "line": "...", "about": "...", "thesis": "...",
                           "points": [{"h": "...", "d": "..."}, ... 4개], "metrics": [["지표", "값"], ... 3개], "risk": "..."}},
  "signals": [{"t": "...", "d": "..."}, ... 2~3개]
}
picks의 순서가 카드 순서다.
"""
import json, os, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from indexer import rebuild
sat = sys.argv[1]
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
W = os.path.join(ROOT, 'work', 'weekly', sat)
cand = json.load(open(os.path.join(W, 'candidates.json'), encoding='utf-8'))
content = json.load(open(os.path.join(W, 'content.json'), encoding='utf-8'))
by_id = {str(r['id']): r for r in cand['candidates']}

def prev_weekday(d):
    d = datetime.date.fromisoformat(d) - datetime.timedelta(days=1)
    while d.weekday() >= 5:
        d -= datetime.timedelta(days=1)
    return d.isoformat()

stocks = []
for rid, c in content['picks'].items():
    r = by_id[rid]
    badges = ['로봇'] if r.get('robot') else ['AI'] if r.get('ai') else []
    stocks.append({**{k: r.get(k) for k in ('id', 'code', 'name', 'sector', 'sub', 'broker', 'title', 'date', 'opinion', 'opinionChanged',
                                            'target', 'targetPrev', 'targetDir', 'price', 'upside', 'mcap', 'url', 'pdf')},
                   'badges': badges, 'basis': prev_weekday(r['date']), 'reason': '주말 다시보기',
                   'pushed': c['pushed'], 'chosen': c['chosen'], 'line': c['line'], 'about': c['about'], 'thesis': c.get('thesis', ''),
                   'points': c['points'], 'metrics': c['metrics'], 'risk': c['risk']})
ops, tg = {}, {'up': 0, 'keep': 0, 'down': 0, 'new': 0, 'none': 0}
for s in stocks:
    ops[s['opinion']] = ops.get(s['opinion'], 0) + 1
    tg[s['targetDir'] if s['targetDir'] in tg else 'none'] += 1
out = {'type': 'weekly', 'date': sat, 'range': cand['range'], 'daysWithData': cand['daysWithData'],
       'basis': prev_weekday(cand['range'][1]),
       'generatedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
       'headline': content['headline'], 'dek': content.get('dek', ''), 'totalReports': len(cand['candidates']),
       'counts': {'opinion': ops, 'target': tg}, 'stocks': stocks, 'signals': content.get('signals', []), 'standouts': content.get('standouts', [])}
json.dump(out, open(os.path.join(ROOT, 'data', f'{sat}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
idx = rebuild(ROOT)
print('저장:', f'data/{sat}.json', '| 카드', len(stocks), '| 날짜 수', len(idx))
