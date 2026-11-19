"""Build a monthly content pack.

    python3 tools/build.py content/packs/2026-12.json            # check + render everything
    python3 tools/build.py content/packs/2026-12.json --check    # checks only (fast)

Outputs:
    media/<month>/<id>.mp4 | .png      committed and served by GitHub Pages
    build/<month>/preview/index.html   review page (publish as an artifact; not committed)
    build/<month>/schedule.json        posts with resolved media URLs, ready for Buffer create_post
"""
import json, os, re, subprocess, sys, html, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from web import passage

MEDIA_BASE = 'https://worshiproomapp.github.io/social/media/'
GUIDES = json.load(open(os.path.join(ROOT, 'content', 'guides.json')))
GUIDE_URLS = {g['url'] for g in GUIDES}

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
    allsrc = ' '.join(srcs.values())
    files = {v['id'] for v in pack['videos']} | {i['id'] for i in pack['images']}
    for n, p in enumerate(pack['posts']):
        tag = f"post {n + 1} ({p['channel']} {p['when']})"
        if p['media'] not in files: errs.append(f'{tag}: unknown media {p["media"]}')
        if p['link'] not in GUIDE_URLS: errs.append(f'{tag}: link not a known guide: {p["link"]}')
        if 'Worship Room' not in p['caption']: errs.append(f'{tag}: caption must name "Worship Room"')
        if p['channel'] == 'pinterest' and not (p.get('title') and p.get('board') and p.get('alt')):
            errs.append(f'{tag}: pinterest needs title, board, alt')
        if p['channel'] == 'instagram' and p['media'].startswith('i') and not p.get('alt'):
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


def schedule_and_preview(pack, month):
    bdir = os.path.join(ROOT, 'build', month); pdir = os.path.join(bdir, 'preview'); os.makedirs(pdir, exist_ok=True)
    vids = {v['id']: v for v in pack['videos']}
    sched = []
    for p in sorted(pack['posts'], key=lambda p: p['when']):
        is_vid = p['media'] in vids
        ext = '.mp4' if is_vid else '.png'
        item = dict(p, url=MEDIA_BASE + month + '/' + p['media'] + ext, kind='video' if is_vid else 'image')
        if is_vid: item['thumbnail_ms'] = vids[p['media']].get('thumbnail_ms', 2000)
        sched.append(item)
        shutil.copy(os.path.join(ROOT, 'media', month, p['media'] + ext), pdir)
    json.dump(sched, open(os.path.join(bdir, 'schedule.json'), 'w'), indent=1, ensure_ascii=False)
    e = lambda s: html.escape(s or '', quote=True)
    cards = []
    for n, p in enumerate(sched, 1):
        fn = os.path.basename(p['url'])
        media = (f'<video controls playsinline preload=metadata src="{fn}#t=0.1"></video>' if p['kind'] == 'video'
                 else f'<img src="{fn}" alt="{e(p.get("alt"))}">')
        rows = ''.join(f'<div class=f><b>{k}</b><div>{e(p[k]).replace(chr(10), "<br>")}</div></div>'
                       for k in ('title', 'caption', 'alt', 'link', 'board') if p.get(k))
        cards.append(f'<article class=card><div class=m>{media}</div><div><div class=meta><span class=ch>{p["channel"]}</span>'
                     f'<span>#{n}</span><span class=when>{e(p["when_label"])}</span></div>{rows}</div></article>')
    page = f'''<!DOCTYPE html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Worship Room social: {month} pack</title>
<style>body{{margin:0;background:#0D0620;color:#ece8f7;font:15px/1.55 system-ui,sans-serif}}.w{{max-width:1080px;margin:0 auto;padding:32px 20px 80px}}
h1{{font:500 28px Georgia,serif;margin:0 0 6px}}.lede{{color:#a59dbf;margin:0 0 24px}}
.card{{display:grid;grid-template-columns:260px 1fr;gap:20px;background:#160d2e;border:1px solid rgba(255,255,255,.09);border-radius:14px;padding:16px;margin-bottom:14px}}
.m video,.m img{{width:100%;border-radius:10px;background:#000}}.meta{{display:flex;gap:12px;margin-bottom:8px;color:#a59dbf}}
.ch{{color:#c4b5fd;font-weight:600;text-transform:capitalize}}.when{{margin-left:auto;color:#fff}}
.f{{border-top:1px solid rgba(255,255,255,.08);padding:8px 0}}.f b{{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#a78bfa}}
@media(max-width:700px){{.card{{grid-template-columns:1fr}}}}</style></head><body><div class=w>
<h1>{month}: {len(sched)} posts</h1><p class=lede>{e(pack.get('note', ''))}</p>{''.join(cards)}</div></body></html>'''
    open(os.path.join(pdir, 'index.html'), 'w').write(page)
    print('preview', pdir)


if __name__ == '__main__':
    path = sys.argv[1]
    pack = json.load(open(path))
    month = pack['month']
    errs = check(pack)
    if errs:
        print('CHECK FAILED:'); [print(' -', x) for x in errs]; sys.exit(1)
    print('checks passed:', len(pack['videos']), 'videos,', len(pack['images']), 'images,', len(pack['posts']), 'posts')
    if '--check' in sys.argv: sys.exit(0)
    build(pack, month)
    schedule_and_preview(pack, month)
