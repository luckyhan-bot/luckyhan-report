"""work/<날짜>의 reports.json + judge.json + picks.json + content.json → data/<날짜>.json, data/index.json 갱신.

content.json (Claude가 PDF를 읽고 직접 다시 쓴 문장)
{
  "headline": "오늘의 한 줄 제목",
  "stocks": {"<리포트 id>": {"line": "업종 지도용 한 줄 설명",
                             "about": ["어떤 회사? 1", "어떤 회사? 2"],
                             "points": ["핵심 포인트 1", ... 4개],
                             "metrics": [["지표명", "값"], ... 3개],
                             "risk": "체크 한 줄"}},
  "signals": [{"t": "시그널 제목", "d": "설명"}, ... 3개],
  "standouts": [{"code": "...", "name": "...", "tag": "유일한 상향", "note": "..."}]
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
        'line': c['line'], 'about': c['about'], 'points': c['points'], 'metrics': c['metrics'], 'risk': c['risk'],
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
    'headline': content['headline'], 'totalReports': len(reports),
    'counts': {'opinion': ops, 'target': tg},
    'stocks': stocks, 'signals': content['signals'], 'standouts': content.get('standouts', []),
}
os.makedirs(os.path.join(ROOT, 'data'), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, 'data', f'{day}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# 날짜 목록 (검색용으로 종목명·코드도 함께)
idx = []
for f in sorted(glob.glob(os.path.join(ROOT, 'data', '20*.json')), reverse=True):
    x = json.load(open(f, encoding='utf-8'))
    idx.append({'date': x['date'], 'headline': x['headline'],
                'stocks': [[s['code'], s['name']] for s in x['stocks']]})
json.dump({'updated': out['generatedAt'], 'days': idx}, open(os.path.join(ROOT, 'data', 'index.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('저장:', f'data/{day}.json', '| 날짜 수', len(idx), '| 의견', ops, '| 목표가', tg)
