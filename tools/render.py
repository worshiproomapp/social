"""Worship Room social renderer, v2: the homepage's "Room in the Margin" language.

The pieces come from the app's homepage (HM-1 / UNI-1):
- the hero's galaxy (pre-rendered from the app's own GalaxyController into assets/bg/),
- Parchment leaves with deckled edges and paper grain (the Reflect leaf),
- Lora display type with one italic emphasis, small lavender/gold tracked labels,
- the hand-drawn "First Light" strokes (night: warm light with glow; paper: gold ink),
- the "Go deeper:" link line and the script wordmark.

Videos: an overlay is rendered frame by frame with a transparent background and composited onto the galaxy loop.
Images: rendered in one pass over a galaxy still.
"""
import base64, json, os, shutil, subprocess, tempfile, zlib
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = lambda *p: os.path.join(ROOT, 'assets', *p)
FPS = 30
CHROME = shutil.which('google-chrome') or shutil.which('chromium') or None


def _b64(path, mime):
    return f'data:{mime};base64,' + base64.b64encode(open(path, 'rb').read()).decode()


_FONTS = None


def fonts_css():
    global _FONTS
    if _FONTS is None:
        f = lambda n: _b64(A('fonts', n), 'font/woff2')
        _FONTS = f"""
@font-face{{font-family:WRLora;src:url({f('lora.woff2')}) format('woff2');font-weight:400 700}}
@font-face{{font-family:WRLora;font-style:italic;src:url({f('lora-italic.woff2')}) format('woff2');font-weight:400 700}}
@font-face{{font-family:WRInter;src:url({f('inter.woff2')}) format('woff2');font-weight:100 900}}
@font-face{{font-family:WRCaveat;src:url({f('caveat-700.woff2')}) format('woff2');font-weight:700}}"""
    return _FONTS


# Deckled edges, verbatim from the homepage (components/homepage/home-classes.ts DECKLE_LEAF / DECKLE_BACK).
DECKLE_LEAF = open(A('deckle-leaf.txt')).read().strip()
DECKLE_BACK = open(A('deckle-back.txt')).read().strip()

# First Light strokes (components/homepage/home-strokes.ts)
STROKE_UNDER = ('M4 26 C 46 15, 98 13, 150 18 S 214 24, 236 14', '0 0 240 40', 3.4)   # heroRoom
STROKE_LEAF = ('M2 10 C 14 2, 36 2, 52 8', '0 0 54 14', 2)                            # leafMark
STROKE_LINK = ('M3 8 C 30 3, 64 11, 97 5', '0 0 100 12', 2.4)                          # alwaysUnderline

BASE_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:var(--w);height:var(--h);overflow:hidden;background:transparent}
.lbl{font-family:WRInter;font-weight:600;text-transform:uppercase;letter-spacing:.22em;line-height:1.2}
.lav{color:#BBA9F0}.gold{color:#DDB872}
.display{font-family:WRLora;font-weight:400;color:#F2EDF8;text-wrap:balance;letter-spacing:-.02em}
.display em{font-style:italic}
.ink path{fill:none;stroke-linecap:round;stroke-linejoin:round}
.ink--night path{stroke:#FFE9C7;filter:drop-shadow(0 0 5px rgba(255,204,140,.5)) drop-shadow(0 0 12px rgba(255,190,120,.25))}
.ink--paper path{stroke:#63400D}
.leafwrap{position:relative;isolation:isolate}
.leafwrap::before{content:'';position:absolute;inset:60px 50px 30px;box-shadow:0 40px 70px 34px rgba(2,1,8,.74);border-radius:24px;z-index:-1}
.leaf-back{position:absolute;inset:0;transform:rotate(3.4deg) translate(15px,5px);background-color:#a39279}
.leaf-back::after{content:'';position:absolute;inset:0;background:linear-gradient(200deg,rgba(40,22,54,.1),rgba(40,22,54,.42))}
.leaf{position:relative;background-color:#D8C9AE;background-image:url(TEX);background-size:210px;color:#2A1F3A}
.leaf::before{content:'';position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(ellipse 90% 64% at 64% 20%,rgba(255,247,226,.22),rgba(255,247,226,0) 70%),
             linear-gradient(196deg,rgba(58,34,74,0) 42%,rgba(58,34,74,.156) 100%)}
.leaf>*{position:relative}
.leadin{font-family:WRLora;font-style:italic;color:#463B55;text-wrap:balance}
.verse{font-family:WRLora;font-weight:400;color:#2A1F3A;letter-spacing:-.005em}
.verse .q{color:#63400D}
.ref{font-family:WRInter;font-weight:600;letter-spacing:.2em;text-transform:uppercase;color:#573709}
.wordmark{font-family:WRCaveat;font-weight:700;color:#fff;line-height:1}
.deeper{font-family:WRInter;color:rgba(242,237,248,.78)}
.deeper b{font-weight:500;color:#F2EDF8;position:relative;white-space:nowrap}
.deeper b svg{position:absolute;left:-2%;bottom:-.42em;width:104%;height:.5em;overflow:visible}
"""


def esc(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;')


def em_html(text, em):
    """Wrap the first occurrence of `em` in <em> (with an id so a stroke can be placed under it)."""
    t = esc(text)
    if em and em in text:
        e = esc(em)
        return t.replace(e, f'<em id=emw>{e}</em>', 1)
    return t


def svg(stroke, cls, attrs=''):
    d, vb, w = stroke
    return f'<svg class="ink {cls}" viewBox="{vb}" preserveAspectRatio="none" {attrs}><path pathLength="1" d="{d}" stroke-width="{w}"/></svg>'


def tex():
    return _b64(A('textures', 'grain-paper.webp'), 'image/webp')


# ───────────────────────────── images ─────────────────────────────
def image_html(spec):
    W, H = spec['w'], spec['h']
    kind = 'pin' if H / W > 1.4 else 'ig'
    bg = _b64(A('bg', f"galaxy-{kind}-{spec.get('bg', 26000)}.jpg"), 'image/jpeg')
    pad = 84 if kind == 'ig' else 78
    head = spec.get('headline_size', 76 if kind == 'ig' else 80)
    vs = spec.get('size', 40 if kind == 'ig' else 52)
    css = BASE_CSS.replace('TEX', tex())
    return f"""<!doctype html><html><head><meta charset=utf-8><style>{fonts_css()}{css}
:root{{--w:{W}px;--h:{H}px}}
body{{background:#08051a url({bg}) center/cover no-repeat}}
.shade{{position:absolute;inset:0;background:
  linear-gradient(180deg,rgba(8,5,26,.55) 0%,rgba(8,5,26,.15) 32%,rgba(8,5,26,0) 50%,rgba(8,5,26,.35) 78%,rgba(8,5,26,.8) 100%)}}
.grain{{position:absolute;inset:0;background:url({_b64(A('textures','grain-dark.webp'),'image/webp')});opacity:.42}}
.wrap{{position:absolute;inset:0;padding:{pad}px {pad}px {int(pad*0.8)}px;display:flex;flex-direction:column}}
.lbl{{font-size:{19 if kind=='ig' else 18}px;margin-bottom:22px}}
.display{{font-size:{head}px;line-height:1.02}}
.mid{{flex:1;display:flex;align-items:center;justify-content:center;padding:10px 0}}
.leafwrap{{width:{spec.get('leaf_w', 760 if kind=='ig' else 724)}px;transform:rotate(-1.6deg)}}
.leaf{{padding:58px 58px 54px;min-height:{spec.get('leaf_h', 660 if kind=='ig' else 700)}px;display:flex;flex-direction:column;justify-content:center}}
.leaf svg.lm{{width:54px;height:14px;display:block;margin-bottom:22px}}
.leadin{{font-size:24px;line-height:1.45;margin-bottom:18px}}
.verse{{font-size:{vs}px;line-height:1.36}}
.ref{{font-size:17px;margin-top:26px}}
.foot{{display:flex;align-items:flex-end;justify-content:space-between;gap:20px}}
.deeper{{font-size:23px;line-height:1.4}}
.wordmark{{font-size:{58 if kind=='ig' else 60}px}}
#emw{{position:relative}}
#emw svg{{position:absolute;left:-4%;bottom:-.2em;width:108%;height:.42em}}
</style></head><body><div class=shade></div><div class=grain></div>
<div class=wrap>
 <div><span class="lbl {spec.get('label_color','lav')}" style="display:block">{esc(spec['kicker'])}</span>
  <h1 class=display>{em_html(spec['headline'], spec.get('headline_em'))}</h1></div>
 <div class=mid><div class=leafwrap><div class=leaf-back style="clip-path:{DECKLE_BACK}"></div>
  <div class=leaf style="clip-path:{DECKLE_LEAF}">
   {svg(STROKE_LEAF, 'ink--paper lm')}
   {f'<p class=leadin>{esc(spec["leadin"])}</p>' if spec.get('leadin') else ''}
   <p class=verse><span class=q>“</span>{esc(spec['quote'])}<span class=q>”</span></p>
   <p class=ref>{esc(spec['ref'])}</p>
  </div></div></div>
 <div class=foot><p class=deeper>Go deeper: <b>{esc(spec['go_deeper'])}{svg(STROKE_LINK,'ink--night')}</b></p>
  <span class=wordmark>Worship Room</span></div>
</div>
<script>
const e=document.getElementById('emw');
if(e){{e.insertAdjacentHTML('beforeend',`{svg(STROKE_UNDER,'ink--night')}`)}}
</script></body></html>"""


def render_images(page, specs, out):
    for spec in specs:
        page.set_viewport_size({'width': spec['w'], 'height': spec['h']})
        hp = os.path.join(tempfile.gettempdir(), f'_{spec["id"]}.html')
        open(hp, 'w').write(image_html(spec))
        page.goto('file://' + hp)
        page.evaluate('document.fonts.ready'); page.wait_for_timeout(250)
        page.screenshot(path=os.path.join(out, spec['id'] + '.png'))
        print('image', spec['id'])


# ───────────────────────────── videos ─────────────────────────────
W, H = 1080, 1920
SPW = 0.34     # reveal pacing, seconds per word


def timeline(spec):
    """(id, t_in, t_out) events and the total length. Phases: hook → leaf (pages) → end card."""
    ev = [('kicker', -10, None), ('hook', -10, 2.3), ('hookline', 0.15, 2.3)]
    t = 2.5
    ev.append(('leaf', t, None))
    t += 0.7
    for pi, p in enumerate(spec['pages']):
        if pi == 0 and spec.get('leadin'):
            ev.append(('lead', t, None)); t += 0.8
        if p.get('label'):
            ev.append((f'p{pi}l', t, None)); t += 0.8
        for ci, c in enumerate(p['chunks']):
            ev.append((f'p{pi}c{ci}', t, None))
            t += max(0.8, len(c.split()) * SPW)
        if p.get('ref'):
            t += 0.25
            ev.append((f'p{pi}r', t, None)); t += 0.6
        words = sum(len(c.split()) for c in p['chunks'])
        t += 1.6 + words * 0.04
        last = pi == len(spec['pages']) - 1
        for i, e in enumerate(ev):
            if e[2] is None and (e[0].startswith(f'p{pi}') or (pi == 0 and e[0] == 'lead' and not last) or (last and e[0] in ('lead', 'leaf'))):
                ev[i] = (e[0], e[1], t)
        t += 0.6
    ev = [(k, a, (t if (k == 'kicker' and b is None) else b)) for k, a, b in ev]
    t += 0.2
    ev.append(('end', t, None))
    ev.append(('endline', t + 0.6, None))
    return ev, round(t + 3.6, 2)


def video_html(spec, ev, total):
    pages = []
    for pi, p in enumerate(spec['pages']):
        prayer = p.get('style') == 'prayer'
        chunks = []
        for ci, c in enumerate(p['chunks']):
            txt = esc(c)
            if ci == 0 and p.get('open'): txt = '<span class=q>“</span>' + txt
            if ci == len(p['chunks']) - 1 and p.get('close'): txt += '<span class=q>”</span>'
            chunks.append(f'<span class=ch id=p{pi}c{ci}>{txt}</span>')
        lab = f'<p class="leadin plabel" id=p{pi}l>{esc(p["label"])}</p>' if p.get('label') else ''
        ref = f'<p class=ref id=p{pi}r>{esc(p["ref"])}</p>' if p.get('ref') else ''
        pages.append(f'<div class="page{" prayer" if prayer else ""}">{lab}<p class=verse>{"".join(chunks)}</p>{ref}</div>')
    css = BASE_CSS.replace('TEX', tex())
    return f"""<!doctype html><html><head><meta charset=utf-8><style>{fonts_css()}{css}
:root{{--w:{W}px;--h:{H}px}}
#scrim{{position:absolute;inset:0;background:radial-gradient(ellipse 80% 38% at 50% 44%,rgba(8,5,26,.55),rgba(8,5,26,0) 72%)}}
#kicker{{position:absolute;top:236px;left:0;right:0;text-align:center;font-size:27px}}
#hook{{position:absolute;left:96px;right:150px;top:330px;height:860px;display:flex;align-items:center;justify-content:center;text-align:center}}
#hook h1{{font-size:104px;line-height:1.06}}
#emw{{position:relative;display:inline-block}}
#hookline{{position:absolute;left:-4%;bottom:-.16em;width:108%;height:.4em}}
#leaf{{position:absolute;left:96px;right:120px;top:360px;height:1020px;display:flex;align-items:center;justify-content:center}}
.leafwrap{{width:100%;transform:rotate(-1.6deg)}}
.leaf{{padding:70px 72px 66px;min-height:860px;display:flex;flex-direction:column;justify-content:center}}
.leaf svg.lm{{width:64px;height:17px;display:block;margin-bottom:26px}}
.stack{{display:grid}}
.page{{grid-area:1/1;display:flex;flex-direction:column;justify-content:center}}
#lead{{font-size:36px;line-height:1.42;margin-bottom:26px}}
.plabel{{font-size:36px;margin-bottom:24px}}
.verse{{font-size:62px;line-height:1.28}}
.page.prayer .verse{{font-style:italic;font-size:52px;line-height:1.38;color:#2A1F3A}}
.ch{{display:block;opacity:0}}
.ref{{font-size:25px;margin-top:38px;opacity:0}}
#end{{position:absolute;left:96px;right:96px;top:300px;height:1000px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;opacity:0}}
#end .wordmark{{font-size:150px;margin-bottom:46px}}
#end .deeper{{font-size:40px;line-height:1.5}}
#end .site{{margin-top:30px;font-family:WRInter;font-weight:600;letter-spacing:.22em;text-transform:uppercase;font-size:22px;color:#BBA9F0}}
#endline path, #hookline path{{stroke-dasharray:1;stroke-dashoffset:1}}
</style></head><body>
<div id=scrim></div>
<div id=kicker class="lbl {spec.get('label_color','lav')}">{esc(spec['kicker'])}</div>
<div id=hook><h1 class=display>{em_html(spec['hook'], spec.get('hook_em'))}</h1></div>
<div id=leaf style="opacity:0"><div class=leafwrap><div class=leaf-back style="clip-path:{DECKLE_BACK}"></div>
 <div class=leaf style="clip-path:{DECKLE_LEAF}">
  {svg(STROKE_LEAF, 'ink--paper lm')}
  {f'<p class=leadin id=lead style="opacity:0">{esc(spec["leadin"])}</p>' if spec.get('leadin') else ''}
  <div class=stack>{''.join(pages)}</div></div></div></div>
<div id=end><span class=wordmark>Worship Room</span>
 <p class=deeper>Go deeper: <b id=endb>{esc(spec['go_deeper'])}{svg(STROKE_LINK,'ink--night',"id=endline")}</b></p>
 <p class=site>worshiproom.com</p></div>
<script>
const e=document.getElementById('emw');
if(e) e.insertAdjacentHTML('beforeend',`{svg(STROKE_UNDER,'ink--night','id=hookline')}`);
const EV={json.dumps(ev)};
const ease=x=>x<0?0:x>1?1:x*x*(3-2*x);
const draw=x=>{{x=x<0?0:x>1?1:x;return 1-Math.pow(1-x,2.2)}};
window.renderAt=function(t){{
 for(const [id,a,b] of EV){{
  if(id==='hookline'){{const p=document.querySelector('#hookline path');if(p){{p.style.strokeDashoffset=(1-draw((t-a)/1.0)).toFixed(3);
     document.getElementById('hookline').style.opacity=(b!==null?1-ease((t-b)/0.45):1).toFixed(3)}};continue}}
  if(id==='endline'){{const p=document.querySelector('#endline path');if(p)p.style.strokeDashoffset=(1-draw((t-a)/1.0)).toFixed(3);continue}}
  const el=document.getElementById(id); if(!el) continue;
  if(id==='hook'){{const o=1-ease((t-b)/0.45);el.style.opacity=o.toFixed(3);el.style.transform='translateY('+(-(1-o)*30).toFixed(1)+'px)';continue}}
  let o=ease((t-a)/(id==='leaf'?0.8:0.75)); if(b!==null) o*=1-ease((t-b)/0.55);
  el.style.opacity=o.toFixed(3);
  if(id==='leaf') el.style.transform='translateY('+((1-ease((t-a)/0.9))*60).toFixed(1)+'px)';
  else if(/^p\\d+c/.test(id)||id==='end') el.style.transform='translateY('+((1-ease((t-a)/0.75))*12).toFixed(1)+'px)';
 }}
}};
renderAt(0);
</script></body></html>"""


def render_videos(page, specs, out):
    """Silent MP4s to out/_silent/<id>.mp4 (overlay composited on the galaxy loop) + timelines."""
    page.set_viewport_size({'width': W, 'height': H})
    sil = os.path.join(out, '_silent'); os.makedirs(sil, exist_ok=True)
    for spec in specs:
        ev, total = timeline(spec)
        hp = os.path.join(tempfile.gettempdir(), f'_{spec["id"]}.html')
        open(hp, 'w').write(video_html(spec, ev, total))
        page.goto('file://' + hp)
        page.evaluate('document.fonts.ready'); page.wait_for_timeout(300)
        fdir = os.path.join(tempfile.gettempdir(), 'frames', spec['id'])
        shutil.rmtree(fdir, ignore_errors=True); os.makedirs(fdir)
        for f in range(int(total * FPS)):
            page.evaluate(f'renderAt({f / FPS})')
            page.screenshot(path=f'{fdir}/{f:05d}.png', omit_background=True)
        # vary where in the galaxy loop each video starts, so a feed of them doesn't look identical
        start = (zlib.crc32(spec['id'].encode()) % 6)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', str(start), '-stream_loop', '-1', '-i', A('bg', 'galaxy-vertical.mp4'),
                        '-framerate', str(FPS), '-i', f'{fdir}/%05d.png',
                        '-filter_complex', '[0:v]setpts=PTS-STARTPTS[bg];[bg][1:v]overlay=0:0:shortest=1,format=yuv420p',
                        '-t', str(total), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-profile:v', 'high',
                        '-r', str(FPS), '-movflags', '+faststart', os.path.join(sil, spec['id'] + '.mp4')], check=True)
        json.dump({'events': ev, 'total': total}, open(os.path.join(sil, spec['id'] + '.timeline.json'), 'w'))
        shutil.rmtree(fdir, ignore_errors=True)
        print('video', spec['id'], f'{total}s')


def launch(p):
    args = ['--allow-file-access-from-files']
    return p.chromium.launch(executable_path=CHROME, args=args) if CHROME else p.chromium.launch(args=args)
