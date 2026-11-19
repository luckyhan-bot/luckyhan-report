"""관심 종목 읽기 → work/portfolio.json
사용: python3 scripts/portfolio.py <luckyhan-app 클론 경로>
1순위: luckyhan-app 의 portfolio-sync 브랜치 portfolio.json (앱이 즐겨찾기·보유를 바꿀 때마다 자동 저장)
2순위: main 브랜치 watchlist.json (즐겨찾기 초기 목록) - 연동 전 임시
"""
import json, os, subprocess, sys
app = sys.argv[1]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'work', 'portfolio.json')
os.makedirs(os.path.dirname(OUT), exist_ok=True)
def git(*a):
    return subprocess.run(['git', '-C', app, *a], capture_output=True, text=True)
git('fetch', '-q', 'origin', 'portfolio-sync')
r = git('show', 'FETCH_HEAD:portfolio.json')
if r.returncode == 0 and r.stdout.strip():
    p = json.loads(r.stdout); p['source'] = 'luckyhan-app portfolio-sync/portfolio.json'
else:
    git('fetch', '-q', 'origin', 'main')
    w = json.loads(git('show', 'FETCH_HEAD:watchlist.json').stdout or '[]')
    p = {'source': 'luckyhan-app main/watchlist.json (연동 전 임시)', 'favs': [{'c': x['code'], 'n': x['name']} for x in w if x.get('code')], 'holds': []}
json.dump(p, open(OUT, 'w'), ensure_ascii=False, indent=1)
print(p['source'], '| 즐겨찾기', len(p.get('favs', [])), '| 보유', len(p.get('holds', [])))
