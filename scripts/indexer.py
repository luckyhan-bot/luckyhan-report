"""data/index.json 다시 만들기 (매일 정리·주말 다시보기 공통)."""
import glob, json, os, datetime

def rebuild(root):
    idx = []
    for f in sorted(glob.glob(os.path.join(root, 'data', '20*.json')), reverse=True):
        x = json.load(open(f, encoding='utf-8'))
        hl = x['headline']
        idx.append({'date': x['date'], 'type': x.get('type', 'daily'), 'headline': ' '.join(hl) if isinstance(hl, list) else hl,
                    'stocks': [[s['code'], s['name']] for s in x['stocks']]})
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    json.dump({'updated': now, 'days': idx}, open(os.path.join(root, 'data', 'index.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return idx
