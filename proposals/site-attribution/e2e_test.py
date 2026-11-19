"""End-to-end attribution test against a local `wrangler dev --local` (nothing deployed)."""
import json, subprocess, sys
from playwright.sync_api import sync_playwright
BASE = 'http://localhost:8787'
FAKE_TS = """window.turnstile={render:(el,o)=>{window.__ts=o;return 1},reset(){},execute(){setTimeout(()=>window.__ts.callback('test-token'),30)}};
if(window.wrTurnstileReady)window.wrTurnstileReady();"""
SITE = '/home/claude/e2e/site'

def d1(sql):
    out = subprocess.run(['npx', 'wrangler', 'd1', 'execute', 'worshiproom-waitlist', '--local', '--json', '--command', sql],
                         cwd=SITE, capture_output=True, text=True, env={'CI': '1', 'WRANGLER_SEND_METRICS': 'false', 'PATH': '/usr/bin:/usr/local/bin:/bin'})
    return json.loads(out.stdout)[0]['results']

def ctx(b):
    c = b.new_context()
    def route(r):
        u = r.request.url
        if u.startswith('https://challenges.cloudflare.com/turnstile'): return r.fulfill(body=FAKE_TS, content_type='text/javascript')
        if u.startswith(BASE): return r.continue_()
        return r.abort()
    c.route('**/*', route)
    return c

def signup(page, email):
    f = page.locator('form[data-signup]').first
    f.locator('input[type=email]').fill(email)
    f.locator('button[type=submit], button:not([type])').first.click()
    page.wait_for_selector('.signup-done', timeout=15000)

SEEN = set()
def next_guide(page):
    SEEN.add(page.evaluate('location.pathname'))
    href = page.evaluate("""seen => [...document.querySelectorAll('a[href^="/guides/"]')].map(a=>a.getAttribute('href')).find(x=>!seen.includes(x.split('#')[0]))""", list(SEEN))
    page.click(f'a[href="{href}"] >> nth=0')
    page.wait_for_load_state('load')
    return page.evaluate('location.pathname')

results = []
def check(name, cond, detail=''):
    results.append((name, bool(cond), detail)); print(('PASS ' if cond else 'FAIL ') + name, detail)

d1('DELETE FROM subscribers'); d1('DELETE FROM landings')
pin = 'utm_source=pinterest&utm_medium=social&utm_campaign=2026-12-pack&utm_content=2026-12-pin-03&utm_term=prayer-for-grief'
with sync_playwright() as p:
    b = p.chromium.launch()
    # A: tracked pin → second guide → third guide → signup
    c = ctx(b); pg = c.new_page()
    pg.goto(f'{BASE}/guides/prayer-for-grief?{pin}'); pg.wait_for_load_state('load')
    check('A1 address bar cleaned', pg.url == f'{BASE}/guides/prayer-for-grief', pg.url)
    check('A2 stored in sessionStorage', 'pinterest' in (pg.evaluate("sessionStorage.getItem('wr_utm')") or ''), pg.evaluate("sessionStorage.getItem('wr_utm')"))
    check('A3 no cookie set', c.cookies() == [], str(c.cookies()))
    g2 = next_guide(pg); g3 = next_guide(pg)
    check('A4 survives two guide-to-guide navigations', 'pinterest' in (pg.evaluate("sessionStorage.getItem('wr_utm')") or ''), f'{g2} -> {g3}')
    pg.reload(); pg.wait_for_load_state('load')
    signup(pg, 'a@example.com')
    r = d1("SELECT * FROM subscribers WHERE email='a@example.com'")[0]
    check('A5 row: platform/campaign/post/term', (r['utm_source'], r['utm_medium'], r['utm_campaign'], r['utm_content'], r['utm_term']) ==
          ('pinterest', 'social', '2026-12-pack', '2026-12-pin-03', 'prayer-for-grief'), json.dumps(r))
    check('A6 row: landing page + signup page', r['landing_path'] == '/guides/prayer-for-grief' and r['source'] == 'coming-soon:' + g3, f"landing={r['landing_path']} signup={r['source']}")
    # B: first touch wins in the same tab
    pg.goto(f'{BASE}/guides/how-to-pray?utm_source=instagram&utm_content=bio'); pg.wait_for_load_state('load')
    check('B1 first touch kept', json.loads(pg.evaluate("sessionStorage.getItem('wr_utm')"))['source'] == 'pinterest')
    c.close()
    # C: direct visit, no link labels
    c = ctx(b); pg = c.new_page(); pg.goto(f'{BASE}/guides/how-to-pray'); signup(pg, 'c@example.com')
    r = d1("SELECT * FROM subscribers WHERE email='c@example.com'")[0]
    check('C1 untracked visit stores nulls', r['utm_source'] is None and r['landing_path'] is None and r['source'] == 'coming-soon:/guides/how-to-pray', json.dumps(r))
    c.close()
    # D: Instagram bio link (platform-level only)
    c = ctx(b); pg = c.new_page()
    pg.goto(f'{BASE}/?utm_source=instagram&utm_medium=social&utm_campaign=profile&utm_content=bio'); pg.wait_for_load_state('load')
    next_guide(pg); signup(pg, 'd@example.com')
    r = d1("SELECT * FROM subscribers WHERE email='d@example.com'")[0]
    check('D1 bio link: platform + "bio", landing /', (r['utm_source'], r['utm_content'], r['landing_path']) == ('instagram', 'bio', '/'), json.dumps(r))
    # E: a new tab without an opener does not inherit attribution (sessionStorage is per tab)
    pg2 = c.new_page(); pg2.goto(f'{BASE}/guides/morning-prayer')
    check('E1 fresh tab has no attribution (documented limit)', pg2.evaluate("sessionStorage.getItem('wr_utm')") is None)
    c.close()
    # F: junk labels are dropped
    c = ctx(b); pg = c.new_page()
    pg.goto(f'{BASE}/guides/how-to-pray?utm_source=%3Cscript%3E&utm_content=x'); pg.wait_for_load_state('load')
    check('F1 invalid source not stored', pg.evaluate("sessionStorage.getItem('wr_utm')") is None)
    c.close()
    b.close()

rows = d1('SELECT path, utm_source, utm_content, visits FROM landings ORDER BY utm_source')
check('G1 landing counts: one per tracked landing, none for reloads/junk',
      sorted((x['utm_source'], x['path'], x['visits']) for x in rows) == [('instagram', '/', 1), ('pinterest', '/guides/prayer-for-grief', 1)], json.dumps(rows))
ok = all(r[1] for r in results)
print(f"\n{sum(r[1] for r in results)}/{len(results)} passed"); sys.exit(0 if ok else 1)
