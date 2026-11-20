"""work/<날짜>의 reports.json + judge.json + picks.json + content.json → data/<날짜>.json, data/index.json 갱신.

content.json (Claude가 PDF를 읽고 직접 다시 쓴 문장)
{
  "headline": ["제목 첫 줄", "둘째 줄(빨강 강조)"],
  "dek": "표지 소개 두 줄",
  "stocks": {"<리포트 id>": {"line": "업종 지도용 한 줄 설명",
                             "about": "어떤 회사? 2~3문장, 핵심어는 **굵게**",
                             "thesis": "증권사 결론 한 줄",
                             "points": [{"h": "굵은 소제목", "d": "1~2문장 설명(용어 풀이 포함)"}, ... 4개],
                             "metrics": [["지표명", "값"], ... 3개],
                             "risk": "체크 한 줄"}},
  "signals": [{"t": "시그널 제목", "d": "여러 리포트를 가로지르는 설명, 종목명·숫자는 **굵게**"}, ... 3개],
  "standouts": [{"dir": "up|down|none", "tag": "유일한 목표가 상향", "code": "...", "name": "...", "note": "..."}]
}
"""
import json, os, sys, glob, datetime

day = sys.argv[1]
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
W = os.path.join(ROOT, 'work', day)
load = lambda n: json.load(open(os.path.join(W, n), encoding='utf-8'))
reports = {r['id']: r for r in load('reports.json')['reports']}
judge = {int(k): v for k, v in load('judge.json').items()}
picks = load('picks.json')
content = load('content.json')

def norm_op(s):
    s = (s or '').strip().upper()
    if s in ('BUY', '매수', 'STRONG BUY', 'OUTPERFORM', 'TRADING BUY', '비중확대'):
        return 'BUY'
    if s in ('HOLD', '중립', 'NEUTRAL', 'MARKETPERFORM', 'MARKET PERFORM'):
        return 'HOLD'
    if s in ('SELL', '매도', 'REDUCE', 'UNDERPERFORM', '비중축소'):
        return 'SELL'
    return 'NR'

prev_day = None
stocks = []
for p in picks:
    r, j, c = reports[p['id']], judge.get(p['id'], {}), content['stocks'][str(p['id'])]
    st = r.get('stock') or {}
    price = r.get('reportPrice') or st.get('prevClose')
    target = r.get('target')
    badges = (['보유'] if p['hold'] else []) + (['즐겨찾기'] if p['fav'] and not p['hold'] else [])
    if j.get('robot'):
        badges.append('로봇')
    elif j.get('ai'):
        badges.append('AI')
    stocks.append({
        'id': r['id'], 'code': r['code'], 'name': r['name'], 'market': st.get('market'),
        'sector': j.get('sector'), 'sub': j.get('sub'), 'badges': badges, 'reason': p['reason'],
        'broker': r['broker'], 'title': r['title'], 'date': r['date'],
        'opinion': norm_op(r.get('opinion')), 'opinionRaw': r.get('opinion'),
        'opinionChanged': bool(j.get('opinion_changed')),
        'target': target, 'targetPrev': j.get('target_prev'), 'targetDir': j.get('target_dir') or 'none',
        'price': price, 'upside': round((target / price - 1) * 100, 1) if target and price else None,
        'mcap': st.get('mcapPrev'),
        'line': c['line'], 'about': c['about'], 'thesis': c.get('thesis', ''), 'points': c['points'], 'metrics': c['metrics'], 'risk': c['risk'],
        'url': r['url'], 'pdf': r.get('pdfUrl'),
    })

ops = {}
for s in stocks:
    ops[s['opinion']] = ops.get(s['opinion'], 0) + 1
tg = {'up': 0, 'keep': 0, 'down': 0, 'new': 0, 'none': 0}
for s in stocks:
    tg[s['targetDir'] if s['targetDir'] in tg else 'none'] += 1

# 기준일 = 리포트 날짜의 전 거래일 (리포트 본문 '현재주가(11/18)' 기준). 주말만 건너뛴다.
d = datetime.date.fromisoformat(day) - datetime.timedelta(days=1)
while d.weekday() >= 5:
    d -= datetime.timedelta(days=1)

out = {
    'date': day, 'basis': d.isoformat(), 'generatedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
    'headline': content['headline'], 'dek': content.get('dek', ''), 'totalReports': len(reports),
    'counts': {'opinion': ops, 'target': tg},
    'stocks': stocks, 'signals': content['signals'], 'standouts': content.get('standouts', []),
}
os.makedirs(os.path.join(ROOT, 'data', 'pool'), exist_ok=True)
# 그날 모든 리포트(뽑힌 것 + 밀린 이유) → data/pool/<날짜>.json  (주말 다시보기 재료)
try:
    skipped = {x['id']: x['skip'] for x in load('skipped.json')}
except FileNotFoundError:
    skipped = {}
pick_reason = {p['id']: p['reason'] for p in picks}
pool = []
for r in reports.values():
    j = judge.get(r['id'], {}); st = r.get('stock') or {}
    pprice = r.get('reportPrice') or st.get('prevClose'); ptg = r.get('target')
    pool.append({'id': r['id'], 'code': r['code'], 'name': r['name'], 'broker': r['broker'], 'title': r['title'], 'date': r['date'],
                 'source': r.get('source', 'naver'), 'opinion': norm_op(r.get('opinion')), 'target': ptg, 'targetPrev': j.get('target_prev'),
                 'targetDir': j.get('target_dir') or 'none', 'opinionChanged': bool(j.get('opinion_changed')),
                 'sector': j.get('sector'), 'sub': j.get('sub'), 'ai': bool(j.get('ai')), 'robot': bool(j.get('robot')),
                 'mcap': st.get('mcapPrev'), 'price': pprice, 'upside': round((ptg / pprice - 1) * 100, 1) if ptg and pprice else None,
                 'url': r['url'], 'pdf': r.get('pdfUrl'), 'readCount': r.get('readCount'),
                 'picked': r['id'] in pick_reason, 'reason': pick_reason.get(r['id']) or skipped.get(r['id'])})
json.dump({'date': day, 'reports': pool}, open(os.path.join(ROOT, 'data', 'pool', f'{day}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(out, open(os.path.join(ROOT, 'data', f'{day}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# 날짜 목록 (검색용으로 종목명·코드도 함께)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from indexer import rebuild
idx = rebuild(ROOT)
print('저장:', f'data/{day}.json', '| 날짜 수', len(idx), '| 의견', ops, '| 목표가', tg)
