"""하루 10종목 고르기.

입력
  work/<날짜>/reports.json   : scripts/fetch.js 결과
  work/<날짜>/judge.json     : 리포트별 판단(업종·AI·로봇·목표가/의견 변경) - Claude가 PDF를 읽고 작성
  work/portfolio.json        : 관심 종목 {"favs":[{"c","n"}], "holds":[{"c","n"}]}
출력
  work/<날짜>/picks.json     : 고른 10개 리포트 id와 고른 이유

규칙 (순서대로 10자리 채우기)
  1단계 관심 종목: 리포트가 있으면 무조건 포함. 10개 초과 시 목표가 변경 있는 것 우선.
  2단계 AI 관련: 시가총액(전일 종가 기준) 큰 순. 1단계 AI 포함 최대 6개.
         로봇 리포트가 있으면 시총과 관계없이 최소 1개.
  3단계 나머지: 목표가 변경 > 투자의견 변경 > 업종이 겹치지 않게(같으면 시총 큰 순).
  같은 종목 리포트가 여럿이면 하나만(목표가 변경 있는 쪽, 다음은 조회수).
"""
import json, sys, os

N, AI_MAX = 10, 6
day = sys.argv[1]
W = os.path.join(os.path.dirname(__file__), '..', 'work')
reports = json.load(open(os.path.join(W, day, 'reports.json')))['reports']
judge = {int(k): v for k, v in json.load(open(os.path.join(W, day, 'judge.json'))).items()}
try:
    pf = json.load(open(os.path.join(W, 'portfolio.json')))
except FileNotFoundError:
    pf = {"favs": [], "holds": []}
favs = {x['c'] for x in pf.get('favs', [])}
holds = {x['c'] for x in pf.get('holds', [])}

def info(r):
    j = judge.get(r['id'], {})
    s = r.get('stock') or {}
    return {**r, **j, 'mcap': s.get('mcapPrev') or 0,
            'tchg': j.get('target_dir') in ('up', 'down'),
            'ochg': bool(j.get('opinion_changed'))}

# 종목당 리포트 하나
best = {}
for r in map(info, reports):
    k = r['code']
    key = (r['tchg'], r['ochg'], r.get('readCount') or 0)
    if k not in best or key > best[k][0]:
        best[k] = (key, r)
cands = [v[1] for v in best.values()]

picked, why = [], {}
def take(r, reason):
    picked.append(r); why[r['id']] = reason
left = lambda: [r for r in cands if r['id'] not in why]
n_ai = lambda: sum(1 for r in picked if r.get('ai') or r.get('robot'))

# 1단계
interest = [r for r in cands if r['code'] in favs or r['code'] in holds]
interest.sort(key=lambda r: (not r['tchg'], not r['ochg'], -r['mcap']))
for r in interest[:N]:
    take(r, '관심 종목(' + ('보유' if r['code'] in holds else '즐겨찾기') + ')')

# 2단계
if len(picked) < N:
    ai = sorted([r for r in left() if r.get('ai') or r.get('robot')], key=lambda r: -r['mcap'])
    robots = [r for r in ai if r.get('robot')]
    need_robot = robots and not any(r.get('robot') for r in picked)
    for r in ai:
        if len(picked) >= N or n_ai() >= AI_MAX:
            break
        slots = min(AI_MAX - n_ai(), N - len(picked))
        if need_robot and not r.get('robot') and slots <= 1:
            continue  # 마지막 AI 자리는 로봇 몫
        take(r, '로봇 대표' if r.get('robot') and need_robot else 'AI 관련 대형주')
        if r.get('robot'):
            need_robot = False
    if need_robot and len(picked) < N:
        take(robots[0], '로봇 대표')

# 3단계 (AI 관련은 이미 한도를 채웠으면 제외)
while len(picked) < N:
    pool = [r for r in left() if not ((r.get('ai') or r.get('robot')) and n_ai() >= AI_MAX)]
    if not pool:
        break
    used = {r.get('sector') for r in picked}
    pool.sort(key=lambda r: (not r['tchg'], not r['ochg'], r.get('sector') in used, -r['mcap']))
    r = pool[0]
    take(r, '목표가 변경' if r['tchg'] else '투자의견 변경' if r['ochg'] else '업종 다양성')

out = [{'id': r['id'], 'code': r['code'], 'name': r['name'], 'reason': why[r['id']],
        'fav': r['code'] in favs, 'hold': r['code'] in holds} for r in picked]
json.dump(out, open(os.path.join(W, day, 'picks.json'), 'w'), ensure_ascii=False, indent=1)
for i, x in enumerate(out, 1):
    print(i, x['code'], x['name'], '-', x['reason'])
