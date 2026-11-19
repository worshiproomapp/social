"""Renders verse videos (1080x1920) and images in the Worship Room pin style with Playwright + ffmpeg."""
import json, os, subprocess, sys, shutil, zlib, tempfile
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, 'assets', 'fonts')
FPS = 30
CHROME = shutil.which('google-chrome') or shutil.which('chromium') or None

import base64
def _b64(n): return "data:font/woff2;base64,"+base64.b64encode(open(f"{FONTS}/{n}","rb").read()).decode()
BASE_CSS = f"""
@font-face {{ font-family: WRLora; src: url({_b64('lora.woff2')}) format('woff2'); font-weight: 400 700; }}
@font-face {{ font-family: WRLora; font-style: italic; src: url({_b64('lora-italic.woff2')}) format('woff2'); font-weight: 400 700; }}
@font-face {{ font-family: WRInter; src: url({_b64('inter.woff2')}) format('woff2'); font-weight: 100 900; }}
@font-face {{ font-family: WRCaveat; src: url({_b64('caveat-700.woff2')}) format('woff2'); font-weight: 700; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width: var(--w); height: var(--h); overflow: hidden; background:#140d2b; }}
#bg {{ position:absolute; inset:0;
  background:
    radial-gradient(ellipse 55% 30% at 50% 47%, rgba(109,40,217,.38), rgba(109,40,217,0) 70%),
    radial-gradient(ellipse 60% 18% at 50% 104%, rgba(120,70,60,.28), rgba(0,0,0,0) 70%),
    linear-gradient(180deg, #1c1633 0%, #1a1331 35%, #150d2b 70%, #130c24 100%); }}
#stars {{ position:absolute; inset:0; }}
.star {{ position:absolute; border-radius:50%; background:#fff; }}
.kicker {{ font-family: WRInter; font-weight:600; letter-spacing:.22em; color:#b9a6f5; text-align:center; }}
.rule {{ width:64px; height:2px; margin:22px auto 0; background:linear-gradient(90deg,transparent,#a78bfa,transparent); }}
.verse {{ font-family: WRLora; font-weight:500; color:#fff; text-align:center; line-height:1.28; }}
.ref {{ font-family: WRInter; font-weight:600; letter-spacing:.16em; color:#b9a6f5; text-align:center; }}
.wordmark {{ font-family: WRCaveat; font-weight:700; color:#fff; text-align:center; }}
.pill {{ display:inline-flex; align-items:center; gap:14px; font-family:WRInter; font-weight:500; color:#fff;
  border:1px solid rgba(255,255,255,.16); background:rgba(255,255,255,.04); border-radius:999px; }}
.pill i {{ display:block; width:10px; height:10px; border-radius:50%; background:#a78bfa; }}
.sub {{ font-family: WRInter; font-weight:400; color:rgba(255,255,255,.82); text-align:center; }}
.q {{ color:#c4b5fd; }}
"""

STARS_JS = """
function mulberry(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
function makeStars(seed, n, W, H){const r=mulberry(seed),box=document.getElementById('stars'),out=[];
 for(let i=0;i<n;i++){const s=document.createElement('div');s.className='star';const sz=r()<.12?2.6+r()*1.4:1+r()*1.4;
  s.style.width=s.style.height=sz+'px';s.style.left=(r()*W)+'px';s.style.top=(r()*H)+'px';
  const base=.25+r()*.6;s.style.opacity=base;box.appendChild(s);out.push({el:s,base,ph:r()*6.28,sp:.6+r()*1.4,big:sz>2.5});}
 return out;}
"""


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;')


# ---------------- images ----------------
def image_html(spec):
    W, H = spec['w'], spec['h']
    tall = H / W > 1.4
    q = esc(spec['quote'])
    return f"""<!doctype html><html><head><meta charset=utf-8><style>{BASE_CSS}
:root{{--w:{W}px;--h:{H}px}}
.wrap{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center}}
.top{{margin-top:{int(H*0.083)}px}} .kicker{{font-size:{26 if W<1050 else 27}px}}
.mid{{flex:1;display:flex;flex-direction:column;justify-content:center;align-items:center;padding:0 {int(W*0.11)}px;margin-top:-{int(H*0.02)}px}}
.verse{{font-size:{spec['size']}px}} .ref{{font-size:28px;margin-top:{int(spec['size']*0.75)}px}}
.foot{{margin-bottom:{int(H*0.064)}px;display:flex;flex-direction:column;align-items:center}}
.sub{{font-size:{27 if tall else 28}px;margin-bottom:22px}} .wordmark{{font-size:{72 if tall else 70}px;line-height:1;margin-bottom:22px}}
.pill{{font-size:26px;padding:16px 28px}}
</style></head><body><div id=bg></div><div id=stars></div>
<div class=wrap><div class=top><div class=kicker>{esc(spec['kicker'])}</div><div class=rule></div></div>
<div class=mid><div class=verse><span class=q>“</span>{q}<span class=q>”</span></div><div class=ref>{esc(spec['ref'])}</div></div>
<div class=foot><div class=sub>{esc(spec['footer'])}</div><div class=wordmark>Worship Room</div><div class=pill><i></i>worshiproom.com</div></div></div>
<script>{STARS_JS} makeStars({zlib.crc32(spec['id'].encode())%9999},{int(W*H/9000)},{W},{H});</script></body></html>"""


def render_images(page, specs, out):
    for spec in specs:
        page.set_viewport_size({'width': spec['w'], 'height': spec['h']})
        hp = os.path.join(tempfile.gettempdir(), f'_{spec["id"]}.html')
        open(hp, 'w').write(image_html(spec))
        page.goto('file://' + hp)
        page.evaluate('document.fonts.ready'); page.wait_for_timeout(300)
        page.screenshot(path=os.path.join(out, spec['id'] + '.png'))
        print('image', spec['id'])
# ---------------- videos ----------------
W, H = 1080, 1920
SPW = 0.36       # seconds per word for reveal pacing
FADE = 0.9


def timeline(spec):
    """Return list of (element_id, t_in, t_out) plus total duration."""
    ev = []
    t = 0.6
    if spec.get('hook'):
        # hook is fully visible on frame 0 (it is the thumbnail and the first thing a scroller sees)
        ev.append(('hook', -10, 1.9))
        t = 2.4
    ev.append(('kicker', 0.2 if not spec.get('hook') else 2.0, None))
    for pi, p in enumerate(spec['pages']):
        start = t
        if p.get('label'):
            ev.append((f'p{pi}l', t, None)); t += 0.9
        for ci, c in enumerate(p['chunks']):
            ev.append((f'p{pi}c{ci}', t, None))
            t += max(0.95, len(c.split()) * SPW)
        if p.get('ref'):
            t += 0.3
            ev.append((f'p{pi}r', t, None)); t += 0.8
        words = sum(len(c.split()) for c in p['chunks'])
        t += 1.8 + words * 0.05   # hold so the whole page can be read
        # page out
        for e in ev:
            if e[0].startswith(f'p{pi}') and e[2] is None:
                ev[ev.index(e)] = (e[0], e[1], t)
        t += 0.7
    # end card
    ev = [(k, a, (t if (k == 'kicker' and b is None) else b)) for k, a, b in ev]
    t += 0.4
    ev.append(('end', t, None))
    total = t + 4.2
    return ev, round(total, 2)


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
        lab = f'<div class="kicker plabel" id=p{pi}l>{esc(p["label"])}</div>' if p.get('label') else ''
        ref = f'<div class=ref id=p{pi}r>{esc(p["ref"])}</div>' if p.get('ref') else ''
        pages.append(f'<div class="page{" prayer" if prayer else ""}">{lab}<div class=verse>{"".join(chunks)}</div>{ref}</div>')
    return f"""<!doctype html><html><head><meta charset=utf-8><style>{BASE_CSS}
:root{{--w:{W}px;--h:{H}px}}
#kick{{position:absolute;top:250px;left:0;right:0}} .kicker{{font-size:32px}}
#hook{{position:absolute;left:90px;right:150px;top:0;bottom:420px;display:flex;align-items:center;justify-content:center;text-align:center;
  font-family:WRLora;font-weight:600;font-size:92px;line-height:1.18;color:#fff;text-wrap:balance}}
.page{{position:absolute;left:90px;right:150px;top:330px;bottom:520px;display:flex;flex-direction:column;justify-content:center;align-items:center}}
.page .verse{{font-size:66px;line-height:1.32}}
.page.prayer .verse{{font-family:WRLora;font-style:italic;font-weight:400;font-size:58px;line-height:1.4;color:#f3efff}}
.plabel{{font-size:28px;margin-bottom:46px}}
.ch{{display:block;opacity:0}}
.ref{{font-size:34px;margin-top:56px;opacity:0}}
#end{{position:absolute;left:90px;right:90px;top:0;bottom:200px;display:flex;flex-direction:column;justify-content:center;align-items:center;opacity:0}}
#end .wordmark{{font-size:150px;line-height:1;margin-bottom:40px}}
#end .sub{{font-size:40px;line-height:1.35;margin-bottom:44px;max-width:820px}}
#end .pill{{font-size:36px;padding:22px 40px}} #end .pill i{{width:14px;height:14px}}
</style></head><body><div id=bg></div><div id=stars></div>
{('<div id=hook>' + esc(spec['hook']) + '</div>') if spec.get('hook') else ''}
<div id=kick><div class=kicker id=kicker>{esc(spec['kicker'])}</div><div class=rule id=kickrule></div></div>
{''.join(pages)}
<div id=end><div class=wordmark>Worship Room</div><div class=sub>{esc(spec['end_line'])}</div><div class=pill><i></i>worshiproom.com</div></div>
<script>{STARS_JS}
const stars=makeStars({zlib.crc32(spec['id'].encode())%9999},230,{W},{H});
const EV={json.dumps(ev)}; const FADE={FADE};
const ease=x=>x<0?0:x>1?1:x*x*(3-2*x);
window.renderAt=function(t){{
 for(const s of stars){{const tw=.55+.45*Math.sin(t*s.sp+s.ph);s.el.style.opacity=(s.base*(s.big?tw:(.75+.25*tw))).toFixed(3);}}
 document.getElementById('bg').style.transform='scale('+(1+t*0.0025).toFixed(4)+')';
 for(const [id,a,b] of EV){{const el=document.getElementById(id); if(!el) continue;
  let o=ease((t-a)/FADE); if(b!==null) o*=1-ease((t-b)/0.7);
  el.style.opacity=o.toFixed(3);
  if(id==='hook'){{el.style.opacity=(1-ease((t-b)/0.5)).toFixed(3);continue;}}
  if(/^p\\d+c/.test(id)||id==='end') el.style.transform='translateY('+((1-ease((t-a)/FADE))*14).toFixed(1)+'px)';
  if(id==='kicker'){{const r=document.getElementById('kickrule'); r.style.opacity=o.toFixed(3);}}
 }}
}};
</script></body></html>"""


def render_videos(page, specs, out):
    """Renders silent MP4s to out/_silent/<id>.mp4 and timelines to out/_silent/<id>.timeline.json."""
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
            page.screenshot(path=f'{fdir}/{f:05d}.jpg', type='jpeg', quality=93)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', f'{fdir}/%05d.jpg',
                        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
                        '-r', str(FPS), '-movflags', '+faststart', os.path.join(sil, spec['id'] + '.mp4')], check=True)
        json.dump({'events': ev, 'total': total}, open(os.path.join(sil, spec['id'] + '.timeline.json'), 'w'))
        shutil.rmtree(fdir, ignore_errors=True)
        print('video', spec['id'], f'{total}s')


def launch(p):
    args = ['--allow-file-access-from-files']
    return p.chromium.launch(executable_path=CHROME, args=args) if CHROME else p.chromium.launch(args=args)
