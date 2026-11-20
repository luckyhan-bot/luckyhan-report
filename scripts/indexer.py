"""data/index.json 다시 만들기 (매일 정리·주말 다시보기 공통)."""
import glob, json, os, datetime, re

def rebuild(root):
    idx = []
    for f in sorted(glob.glob(os.path.join(root, 'data', '20*.json')), reverse=True):
        x = json.load(open(f, encoding='utf-8'))
        hl = x['headline']
        idx.append({'date': x['date'], 'type': x.get('type', 'daily'), 'headline': ' '.join(hl) if isinstance(hl, list) else hl,
                    'stocks': [[s['code'], s['name']] for s in x['stocks']]})
    build_search(root)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    json.dump({'updated': now, 'days': idx}, open(os.path.join(root, 'data', 'index.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return idx


def _plain(t):
    return re.sub(r'\*\*(.+?)\*\*', r'\1', str(t or ''))

def build_search(root):
    """전문 검색용: 카드별 텍스트 조각 → data/search.json
    항목: [날짜, 카드번호(-1=총정리), 종목명, 종목코드, 항목명, 문장]"""
    rows = []
    for f in sorted(glob.glob(os.path.join(root, 'data', '20*.json')), reverse=True):
        x = json.load(open(f, encoding='utf-8'))
        d = x['date']
        for i, s in enumerate(x['stocks']):
            card = i + 3
            add = lambda label, t: rows.append([d, card, s['name'], s['code'], label, _plain(t)]) if t else None
            add('리포트 제목', f"{s['broker']} · {s['title']}")
            add('업종', f"{s.get('sector')} › {s.get('sub')} — {s.get('line', '')}")
            about = s.get('about'); add('어떤 회사?', ' '.join(about) if isinstance(about, list) else about)
            add('증권사 결론', s.get('thesis'))
            if s.get('pushed'): add('왜 밀렸나', s['pushed'])
            if s.get('chosen'): add('왜 골랐나', s['chosen'])
            for pt in s.get('points', []):
                add('핵심 포인트', f"{pt['h']} — {pt['d']}" if isinstance(pt, dict) else pt)
            add('핵심 지표', ' · '.join(f'{k} {v}' for k, v in s.get('metrics', [])))
            add('체크', s.get('risk'))
        for g in x.get('signals', []):
            rows.append([d, -1, '총정리', '', '시그널', _plain(f"{g['t']} — {g['d']}")])
    json.dump(rows, open(os.path.join(root, 'data', 'search.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
