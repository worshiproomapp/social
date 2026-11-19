"""Build a monthly content pack.

    python3 tools/build.py content/packs/2026-12.json            # check + render everything
    python3 tools/build.py content/packs/2026-12.json --check    # checks only (fast)

Outputs:
    media/<month>/<id>.mp4 | .png      committed and served by GitHub Pages
    previews/<month>/index.html        review page, committed and served by Pages (uses the media/ URLs)
    build/<month>/schedule.json        posts with resolved media URLs, tracked links and alt text, ready for Buffer
"""
import json, os, re, subprocess, sys, html, shutil
from urllib.parse import urlencode
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from web import passage

MEDIA_BASE = 'https://worshiproomapp.github.io/social/media/'
GUIDES = json.load(open(os.path.join(ROOT, 'content', 'guides.json')))
GUIDE_URLS = {g['url'] for g in GUIDES}
PREVIEW_BASE = 'https://worshiproomapp.github.io/social/previews/'
PURPOSES = ('discover', 'save', 'visit')  # reach new people · be saved/shared · send someone to the guide
CH = {'tiktok': 'tt', 'instagram': 'ig', 'pinterest': 'pin'}


def guide_slug(url):
    return url.rstrip('/').rsplit('/', 1)[-1] or 'home'


def guide_text(url):
    p = os.path.join(ROOT, 'content', 'guides-text', guide_slug(url) + '.txt')
    return open(p).read() if os.path.exists(p) else ''


def utm(link, channel, month, post_id, topic):
    """Tracked link: utm_source=<platform>, utm_medium=social, utm_campaign=<month>-pack, utm_content=<post id>, utm_term=<guide>."""
    q = urlencode({'utm_source': channel, 'utm_medium': 'social', 'utm_campaign': f'{month}-pack',
                   'utm_content': post_id, 'utm_term': topic})
    return link + ('&' if '?' in link else '?') + q


def soft(s):
    return re.sub(r'\s+', ' ', s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')).strip().lower()


def unsourced(text, source):
    """Clauses of `text` that do not appear in the guide text. Context and answers must come from our own guides."""
    src = soft(source)
    bad = []
    for clause in re.split(r'(?<=[.!?:;])\s+|\s+[—–]\s+', soft(text)):
        c = clause.strip(' "\'.,;:!?')
        if len(c.split()) >= 4 and c not in src: bad.append(clause)
    return bad

# Content rules (see CLAUDE.md). Case-insensitive regexes that must never appear in public text.
BANNED = [  # (regex, reason, case_sensitive)
    (r'\bWEB\b|World English Bible', 'translation label', True),
    (r'\bchallenges?\b', 'Challenges feature', False), (r'\bmeditat', 'Meditate feature', False),
    (r'local support|celebrate recovery|counselor|counseling|therap', 'counseling/local support', False),
    (r'prayer ai', '"prayer AI"', False), (r'\bfriends?\b|\bmessaging\b', 'friends/messaging', False),
    (r'admin@', 'admin email', False), (r'\bcure[sd]?\b|guarantee', 'promises', False),
    (r'(?:\bapp\b|worship room)[^.\n]{0,40}\bfree\b(?! to start)|\bfree app\b', 'blanket "free" (say "free to start")', False),
    (r'colour|behaviour|favour|honour|centre\b|realis|organis|recognis|apologis|travell|judgement', 'British spelling', False),
    (r'\bEric\b|Champlin', 'founder name', True),
]


def norm(s):
    return re.sub(r'[\s“”"]+', ' ', s).strip()


def check(pack):
    errs = []
    srcs = {}
    def src(v): return ' '.join(passage(b, c, a, z) for b, c, a, z in v)
    for v in pack['videos']:
        text = ' '.join(c for p in v['pages'] if not p.get('style') for c in p['chunks'])
        s = src(v['verify']); srcs[v['id']] = s
        if norm(text) != norm(s): errs.append(f"{v['id']}: verse text != WEB\n   have: {text}\n   WEB:  {s}")
        if v.get('music') not in ('D', 'F', 'G'): errs.append(f"{v['id']}: music must be D, F or G")
        if pack.get('template', 1) >= 2:
            for k in ('hook', 'kicker', 'go_deeper'):
                if not v.get(k): errs.append(f"{v['id']}: missing {k}")
            if v.get('hook_em') and v['hook_em'] not in v.get('hook', ''): errs.append(f"{v['id']}: hook_em not in hook")
    for i in pack['images']:
        s = src(i['verify']); srcs[i['id']] = s
        if norm(i['quote']) != norm(s): errs.append(f"{i['id']}: quote != WEB\n   have: {i['quote']}\n   WEB:  {s}")
        if pack.get('template', 1) >= 2:
            for k in ('kicker', 'headline', 'go_deeper'):
                if not i.get(k): errs.append(f"{i['id']}: missing {k}")
            if i.get('headline_em') and i['headline_em'] not in i.get('headline', ''): errs.append(f"{i['id']}: headline_em not in headline")
    for c in pack.get('carousels', []):
        if not 3 <= len(c['slides']) <= 10: errs.append(f"{c['id']}: carousels need 3–10 slides")
        if c['slides'][0]['kind'] != 'cover' or c['slides'][-1]['kind'] != 'end': errs.append(f"{c['id']}: first slide is the cover, last is the end card")
        for k in ('kicker', 'go_deeper', 'link'):
            if not c.get(k): errs.append(f"{c['id']}: missing {k}")
        gt = guide_text(c.get('link', ''))
        if not gt: errs.append(f"{c['id']}: no guide text for {c.get('link')} (content/guides-text/)")
        for n, sl in enumerate(c['slides'], 1):
            if sl['kind'] == 'verse':
                ws = src(sl['verify']); srcs[f"{c['id']}#{n}"] = ws
                if norm(sl['quote']).strip('…. ') not in norm(ws) or len(sl['quote']) < 0.6 * len(ws):
                    errs.append(f"{c['id']} slide {n}: quote != WEB\n   have: {sl['quote']}\n   WEB:  {ws}")
            claim = ' '.join([sl.get('heading', '')] + sl.get('body', []) + [sl.get('note', '')]).strip()
            if claim and sl.get('voice') != 'prayer':
                for b in unsourced(claim, gt): errs.append(f"{c['id']} slide {n}: not in the linked guide (keep context and answers to our own guide text): “{b[:70]}”")
    for v in pack['videos']:
        for p in v['pages']:
            if p.get('style') == 'answer':
                for b in unsourced(' '.join(p['chunks']), guide_text(v.get('link', ''))):
                    errs.append(f"{v['id']}: answer page not in the linked guide: “{b[:70]}”")
    allsrc = ' '.join(srcs.values())
    files = {v['id'] for v in pack['videos']} | {i['id'] for i in pack['images']} | {c['id'] for c in pack.get('carousels', [])}
    car_ids = {c['id'] for c in pack.get('carousels', [])}
    exps = {e['name']: e for e in pack.get('experiments', [])}
    for e in exps.values():
        for k in ('hypothesis', 'metric', 'arms', 'min_per_arm'):
            if not e.get(k): errs.append(f"experiment {e['name']}: missing {k}")
    ids = [p.get('id') for p in pack['posts']]
    if pack.get('template', 1) >= 3 and len(set(ids)) != len(ids): errs.append('post ids must be unique')
    for n, p in enumerate(pack['posts']):
        tag = f"post {n + 1} ({p['channel']} {p['when']})"
        if p['media'] not in files: errs.append(f'{tag}: unknown media {p["media"]}')
        if pack.get('template', 1) >= 3:
            if not p.get('id'): errs.append(f'{tag}: missing id')
            if p.get('purpose') not in PURPOSES: errs.append(f'{tag}: purpose must be one of {PURPOSES}')
            x = p.get('experiment')
            if x and (x.get('name') not in exps or x.get('arm') not in exps[x['name']]['arms']): errs.append(f'{tag}: unknown experiment/arm {x}')
            if p['media'] in car_ids and p['channel'] == 'pinterest': errs.append(f'{tag}: Pinterest takes one image, not a carousel')
        if p['link'] not in GUIDE_URLS: errs.append(f'{tag}: link not a known guide: {p["link"]}')
        if 'Worship Room' not in p['caption']: errs.append(f'{tag}: caption must name "Worship Room"')
        if p['channel'] == 'pinterest' and not (p.get('title') and p.get('board') and p.get('alt')):
            errs.append(f'{tag}: pinterest needs title, board, alt')
        if p['channel'] == 'instagram' and p['media'] not in car_ids and p['media'].startswith('i') and not p.get('alt'):
            errs.append(f'{tag}: instagram image needs alt')
        if p['caption'].count('!') > 1: errs.append(f'{tag}: too many exclamation points')
        if len(re.findall(r'#\w+', p['caption'])) > 5: errs.append(f'{tag}: more than 5 hashtags')
        for field in ('caption', 'alt', 'title'):
            t = p.get(field, '')
            for q in re.findall(r'“([^”]+)”', t):
                if len(q.split()) >= 6 and norm(q) not in norm(allsrc):
                    errs.append(f'{tag}: quoted text in {field} not found in this pack\'s WEB passages: “{q[:60]}…”')
            for rx, why, cs in BANNED:
                if re.search(rx, t, 0 if cs else re.I): errs.append(f'{tag}: {field} breaks rule: {why}')
    for v in pack['videos']:
        blob = ' '.join([v.get('hook', ''), v['kicker'], v.get('end_line', ''), v.get('go_deeper', ''), v.get('leadin', '')] + [c for p in v['pages'] for c in p['chunks']])
        for rx, why, cs in BANNED:
            if re.search(rx, blob, 0 if cs else re.I): errs.append(f"{v['id']}: on-screen text breaks rule: {why}")
    for c in pack.get('carousels', []):
        blob = ' '.join([c.get('kicker', ''), c.get('go_deeper', '')] + [' '.join([sl.get(k, '') if isinstance(sl.get(k), str) else ' '.join(sl.get(k, [])) for k in ('headline', 'sub', 'heading', 'body', 'note', 'close', 'label')]) for sl in c['slides']])
        if blob.count('!') > 1: errs.append(f"{c['id']}: more than one exclamation point")
        for rx, why, cs in BANNED:
            if re.search(rx, blob, 0 if cs else re.I): errs.append(f"{c['id']}: on-screen text breaks rule: {why}")
    for i in pack['images']:
        blob = ' '.join([i.get('kicker', ''), i.get('headline', ''), i.get('leadin', ''), i.get('go_deeper', ''), i.get('footer', '')])
        for rx, why, cs in BANNED:
            if re.search(rx, blob, 0 if cs else re.I): errs.append(f"{i['id']}: on-screen text breaks rule: {why}")
    return errs


def build(pack, month):
    import render, music
    from playwright.sync_api import sync_playwright
    out = os.path.join(ROOT, 'media', month); os.makedirs(out, exist_ok=True)
    with sync_playwright() as p:
        b = render.launch(p); page = b.new_page()
        render.render_images(page, pack['images'], out)
        render.render_videos(page, pack['videos'], out)
        render.render_carousels(page, pack.get('carousels', []), out)
        b.close()
    sil = os.path.join(out, '_silent')
    for v in pack['videos']:
        tl = json.load(open(os.path.join(sil, v['id'] + '.timeline.json')))
        wav = os.path.join(sil, v['id'] + '.wav')
        music.make(v['music'], tl['total'], wav, v['id'])
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', os.path.join(sil, v['id'] + '.mp4'), '-i', wav,
                        '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest',
                        '-movflags', '+faststart', os.path.join(out, v['id'] + '.mp4')], check=True)
        p0 = [e for e in tl['events'] if e[0].startswith('p0')][0][2]
        v['thumbnail_ms'] = int((p0 - 0.5) * 1000)
        v['seconds'] = tl['total']
    shutil.rmtree(sil)


def carousel_alt(c, sl, n):
    bg = 'Parchment card on a purple galaxy background' if sl['kind'] in ('verse', 'text') else 'Purple galaxy background'
    parts = {'cover': lambda: f"{c['kicker']}: {sl['headline']} {sl.get('sub', '')} Swipe.",
             'verse': lambda: f"“{sl['quote']}” {sl['ref']}. {sl.get('note', '')}",
             'text': lambda: f"{sl['heading']} {' '.join(sl['body'])}",
             'end': lambda: f"Worship Room. {sl.get('close', '')} Go deeper: {c['go_deeper']}. worshiproom.com."}
    return re.sub(r'\s+', ' ', f"Slide {n} of {len(c['slides'])}. {bg}. {parts[sl['kind']]()}").strip()


def schedule_and_preview(pack, month):
    bdir = os.path.join(ROOT, 'build', month); os.makedirs(bdir, exist_ok=True)
    pdir = os.path.join(ROOT, 'previews', month); os.makedirs(pdir, exist_ok=True)
    vids = {v['id']: v for v in pack['videos']}
    cars = {c['id']: c for c in pack.get('carousels', [])}
    sched = []
    for p in sorted(pack['posts'], key=lambda p: p['when']):
        base = MEDIA_BASE + month + '/'
        item = dict(p, guide=guide_slug(p['link']))
        pid = p.get('id') or f"{month}-{CH[p['channel']]}-{p['when'][5:10]}"
        item['id'] = pid
        item['tracked_link'] = utm(p['link'], p['channel'], month, pid, item['guide'])
        if p['media'] in vids:
            item.update(kind='video', url=base + p['media'] + '.mp4', thumbnail_ms=vids[p['media']].get('thumbnail_ms', 2000))
        elif p['media'] in cars:
            c = cars[p['media']]; size = 'tt' if p['channel'] == 'tiktok' else 'ig'
            item.update(kind='carousel', images=[{'url': f"{base}{c['id']}-{size}-{n:02d}.png", 'alt': carousel_alt(c, sl, n)}
                                                 for n, sl in enumerate(c['slides'], 1)])
        else:
            item.update(kind='image', url=base + p['media'] + '.png')
        sched.append(item)
    json.dump(sched, open(os.path.join(bdir, 'schedule.json'), 'w'), indent=1, ensure_ascii=False)
    os.makedirs(os.path.join(ROOT, 'content', 'schedules'), exist_ok=True)  # committed: analyze.py joins metrics to it
    json.dump(sched, open(os.path.join(ROOT, 'content', 'schedules', month + '.json'), 'w'), indent=1, ensure_ascii=False)
    e = lambda s: html.escape(s or '', quote=True)
    rel = '../../media/' + month + '/'
    cards = []
    for n, p in enumerate(sched, 1):
        if p['kind'] == 'video':
            media = f'<video controls playsinline preload=metadata src="{rel}{os.path.basename(p["url"])}#t=0.1"></video>'
        elif p['kind'] == 'carousel':
            media = '<div class=strip>' + ''.join(f'<img loading=lazy src="{rel}{os.path.basename(i["url"])}" alt="{e(i["alt"])}">' for i in p['images']) + '</div>'
        else:
            media = f'<img src="{rel}{os.path.basename(p["url"])}" alt="{e(p.get("alt"))}">'
        x = p.get('experiment')
        rows = ''.join(f'<div class=f><b>{k}</b><div>{e(v).replace(chr(10), "<br>")}</div></div>' for k, v in
                       [('purpose', p.get('purpose')), ('experiment', x and f"{x['name']} · arm {x['arm']}"), ('title', p.get('title')),
                        ('caption', p.get('caption')), ('alt', p.get('alt')), ('board', p.get('board')),
                        ('tracked link' if p['channel'] == 'pinterest' else 'guide', p['tracked_link'] if p['channel'] == 'pinterest' else p['link'])] if v)
        cards.append(f'<article class=card><div class=m>{media}</div><div><div class=meta><span class=ch>{p["channel"]}</span>'
                     f'<span>#{n} · {e(p["id"])}</span><span class=when>{e(p["when_label"])}</span></div>{rows}</div></article>')
    exp = ''.join(f'<li><b>{e(x["name"])}</b>: {e(x["hypothesis"])} Metric: {e(x["metric"])}; arms {e(" vs ".join(x["arms"]))}; '
                  f'judged at {x["min_per_arm"]}+ posts per arm.</li>' for x in pack.get('experiments', []))
    page = f'''<!DOCTYPE html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<meta name=robots content="noindex,nofollow"><title>Worship Room social: {month} pack</title>
<style>body{{margin:0;background:#0D0620;color:#ece8f7;font:15px/1.55 system-ui,sans-serif}}.w{{max-width:1080px;margin:0 auto;padding:32px 20px 80px}}
h1{{font:500 28px Georgia,serif;margin:0 0 6px}}.lede{{color:#a59dbf;margin:0 0 24px}}ul{{color:#cfc7e6}}
.card{{display:grid;grid-template-columns:260px 1fr;gap:20px;background:#160d2e;border:1px solid rgba(255,255,255,.09);border-radius:14px;padding:16px;margin-bottom:14px}}
.m video,.m>img{{width:100%;border-radius:10px;background:#000}}.strip{{display:flex;gap:6px;overflow-x:auto}}.strip img{{width:200px;border-radius:8px}}
.meta{{display:flex;gap:12px;margin-bottom:8px;color:#a59dbf}}
.ch{{color:#c4b5fd;font-weight:600;text-transform:capitalize}}.when{{margin-left:auto;color:#fff}}
.f{{border-top:1px solid rgba(255,255,255,.08);padding:8px 0;word-break:break-word}}.f b{{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#a78bfa}}
@media(max-width:700px){{.card{{grid-template-columns:1fr}}}}</style></head><body><div class=w>
<h1>{month}: {len(sched)} posts</h1><p class=lede>{e(pack.get('note', ''))}</p>{f"<h2>Experiments</h2><ul>{exp}</ul>" if exp else ""}{''.join(cards)}</div></body></html>'''
    open(os.path.join(pdir, 'index.html'), 'w').write(page)
    print('preview', PREVIEW_BASE + month + '/')


if __name__ == '__main__':
    path = sys.argv[1]
    pack = json.load(open(path))
    month = pack['month']
    errs = check(pack)
    if errs:
        print('CHECK FAILED:'); [print(' -', x) for x in errs]; sys.exit(1)
    print('checks passed:', len(pack['videos']), 'videos,', len(pack['images']), 'images,', len(pack.get('carousels', [])), 'carousels,', len(pack['posts']), 'posts')
    if '--check' in sys.argv: sys.exit(0)
    build(pack, month)
    schedule_and_preview(pack, month)
