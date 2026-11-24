"""Performance analysis with denominators and sample-size rules.

    python3 tools/analyze.py metrics/2026-12-01.json [--out content/reports/2026-12-01.md]

Input: a JSON list of Buffer post nodes from `list_posts` (status sent, includeMetrics true), saved as-is.
It joins each post to its pack entry in content/schedules/*.json by media URL and channel, so every row
carries post id, purpose, format, topic (guide) and experiment arm.

Rules it enforces (so a quiet month never turns into a confident rewrite):
  - Too early: TikTok/Instagram posts under 3 days old, Pinterest pins under 30 days old, are listed but
    excluded from comparisons. Pinterest distribution builds over weeks to months.
  - Every rate shows its denominator ("4 saves / 210 reach = 1.9 per 100").
  - A comparison is a FINDING only when each group has >= MIN_POSTS posts and >= MIN_DENOM total reach
    (impressions on Pinterest) and the rates differ by >= 1.5x. Anything less is a HYPOTHESIS to test.
"""
import json, os, sys, glob, datetime as dt
from collections import defaultdict
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_POSTS, MIN_DENOM, RATIO = 4, 300, 1.5
TOO_EARLY = {'tiktok': 3, 'instagram': 3, 'pinterest': 30}


def _utc(s):
    return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(dt.timezone.utc).replace(second=0, microsecond=0)


def load_schedule():
    idx = {}
    for f in glob.glob(os.path.join(ROOT, 'content', 'schedules', '*.json')):
        for p in json.load(open(f)):
            urls = [p['url']] if p.get('url') else [i['url'] for i in p.get('images', [])]
            for u in urls: idx[(p['channel'], os.path.basename(u))] = p
            # Buffer re-hosts TikTok videos under its own URL, so also index by channel + scheduled time
            if p.get('when'): idx[(p['channel'], _utc(p['when']))] = p
    return idx


def metric(node, *types):
    m = {x['type']: x['value'] for x in node.get('metrics') or []}
    for t in types:
        if t in m and m[t] is not None: return m[t]
    for k, v in m.items():  # e.g. averageWatchTime / avgWatchTime
        if any(t.lower() in k.lower() for t in types) and v is not None: return v
    return None


def rows(nodes, now):
    sched = load_schedule()
    out = []
    for n in nodes:
        n = n.get('node', n)
        ch = n.get('channelService')
        src = [a.get('source', '') for a in n.get('assets') or []]
        p = next((sched[(ch, os.path.basename(s))] for s in src if (ch, os.path.basename(s)) in sched), None)
        if p is None and n.get('dueAt'): p = sched.get((ch, _utc(n['dueAt'])), {})
        p = p or {}
        sent = dt.datetime.fromisoformat((n.get('sentAt') or n['dueAt']).replace('Z', '+00:00'))
        age = (now - sent).total_seconds() / 86400
        kind = p.get('kind') or ('video' if any(s.endswith('.mp4') for s in src) else ('carousel' if len(src) > 1 else 'image'))
        denom = metric(n, 'impressions') if ch == 'pinterest' else metric(n, 'reach', 'views')
        out.append(dict(id=p.get('id', n['id']), channel=ch, kind=kind, purpose=p.get('purpose', '?'), topic=p.get('guide', '?'),
                        arm=(p.get('experiment') or {}).get('arm'), exp=(p.get('experiment') or {}).get('name'),
                        sent=sent.date().isoformat(), age=round(age, 1), early=age < TOO_EARLY.get(ch, 3),
                        denom=denom or 0, saves=metric(n, 'saves') or 0, shares=metric(n, 'shares') or 0,
                        comments=metric(n, 'comments') or 0, likes=metric(n, 'reactions', 'likes') or 0,
                        clicks=metric(n, 'outboundClicks', 'linkClicks') , closeups=metric(n, 'clicks') if ch == 'pinterest' else None,
                        follows=metric(n, 'follows'), watch=metric(n, 'averageTimeWatched', 'averageWatchTime', 'avgWatchTime'), seconds=p.get('seconds')))
    return out


def rate(num, den, per=100):
    return None if not den else num / den * per


def fmt(num, den, label, per=100):
    return f"{num} {label} / {den} = {rate(num, den, per):.1f} per {per}" if den else f"{num} {label} / 0 (no denominator)"


def compare(rs, key, num, label):
    groups = defaultdict(list)
    for r in rs:
        if r[key] not in (None, '?'): groups[r[key]].append(r)
    if len(groups) < 2: return []
    lines, rates = [], {}
    for g, items in sorted(groups.items()):
        n, d = sum(r[num] or 0 for r in items), sum(r['denom'] for r in items)
        rates[g] = (rate(n, d), len(items), d)
        lines.append(f"  - {g}: {len(items)} posts, {fmt(n, d, label)}")
    ok = all(c >= MIN_POSTS and d >= MIN_DENOM for _, c, d in rates.values())
    vals = sorted((v for v, _, _ in rates.values() if v is not None), reverse=True)
    strong = ok and len(vals) >= 2 and vals[-1] > 0 and vals[0] / vals[-1] >= RATIO
    tag = 'FINDING' if strong else 'HYPOTHESIS (sample too small or gap too narrow; keep testing)'
    return [f"- {label} by {key}: {tag}"] + lines


def watch_compare(rs):
    """Average watch as a share of video length, per arm (the tt-pace metric). Same FINDING rules."""
    groups = defaultdict(list)
    for r in rs:
        if r['arm'] and r['watch'] is not None and r['seconds']: groups[r['arm']].append(r['watch'] / r['seconds'])
    if len(groups) < 2: return []
    rates = {a: (sum(v) / len(v), len(v)) for a, v in groups.items()}
    ok = all(n >= MIN_POSTS for _, n in rates.values())
    vals = sorted((v for v, _ in rates.values()), reverse=True)
    strong = ok and vals[-1] > 0 and vals[0] / vals[-1] >= RATIO
    tag = 'FINDING' if strong else 'HYPOTHESIS (fewer than %d posts per arm or gap under %.1fx; no winner yet)' % (MIN_POSTS, RATIO)
    return [f"- average watch % by arm: {tag}"] + [f"  - {a}: {n} posts, {v * 100:.0f}% of length on average" for a, (v, n) in sorted(rates.items())]


def report(rs):
    L = [f"# Performance report, {dt.date.today().isoformat()}", '',
         f"Rules: findings need >= {MIN_POSTS} posts and >= {MIN_DENOM} reach/impressions per group and a >= {RATIO}x gap. "
         f"Too early: TikTok/Instagram < 3 days, Pinterest < 30 days.", '']
    for ch in ('tiktok', 'instagram', 'pinterest'):
        cr = [r for r in rs if r['channel'] == ch]
        if not cr: continue
        ready = [r for r in cr if not r['early']]
        den = 'impressions' if ch == 'pinterest' else 'reach'
        L += [f"## {ch.title()}: {len(cr)} posts ({len(ready)} old enough to judge)", '']
        for r in sorted(cr, key=lambda r: r['sent']):
            bits = [f"{r['denom']} {den}", f"saves {r['saves']}", f"shares {r['shares']}", f"comments {r['comments']}", f"likes {r['likes']}"]
            if r['closeups'] is not None: bits.append(f"closeups {r['closeups']}")
            if r['clicks'] is not None: bits.append(f"outbound clicks {r['clicks']}")
            if r['follows'] is not None: bits.append(f"follows {r['follows']}")
            if r['watch'] is not None:
                bits.append(f"avg watch {r['watch']}s" + (f" of {r['seconds']:.0f}s ({r['watch'] / r['seconds'] * 100:.0f}%)" if r['seconds'] else ''))
            L.append(f"- {r['sent']} {r['id']} [{r['kind']}, {r['purpose']}, {r['topic']}{', arm ' + r['arm'] if r['arm'] else ''}]"
                     f"{' (too early)' if r['early'] else ''}: " + ', '.join(bits))
        L.append('')
        if ready:
            tot = sum(r['denom'] for r in ready)
            L += [f"Totals (judgeable posts): {fmt(sum(r['saves'] for r in ready), tot, 'saves')}; "
                  f"{fmt(sum(r['shares'] for r in ready), tot, 'shares')}; {fmt(sum(r['comments'] for r in ready), tot, 'comments')}", '']
            for key in ('kind', 'purpose', 'topic'):
                for num, label in (('saves', 'saves'), ('shares', 'shares')):
                    L += compare(ready, key, num, label)
            for exp in sorted({r['exp'] for r in ready if r['exp']}):
                er = [r for r in ready if r['exp'] == exp]
                L.append(f"- experiment {exp}: " + ', '.join(f"{a} {sum(r['arm'] == a for r in er)} judgeable posts" for a in sorted({r['arm'] for r in er})))
                if exp.startswith('tt-pace') or ch == 'tiktok':
                    L += watch_compare(er)
                for num, label in (('saves', 'saves'), ('shares', 'shares')):
                    L += compare(er, 'arm', num, label)
            L.append('')
    L += ['## Not measured here', '',
          '- Buffer does not return TikTok/Instagram profile visits, link-in-bio taps, retention curves, or Pinterest outbound clicks reliably; check native analytics.',
          '- Website visits come from Cloudflare Web Analytics (by path and referrer); waitlist signups by page come from D1 (`npm run list:count`). Neither is available to this script.']
    return '\n'.join(L)


if __name__ == '__main__':
    nodes = json.load(open(sys.argv[1]))
    if isinstance(nodes, dict): nodes = [e['node'] for e in nodes.get('edges', [])]
    md = report(rows(nodes, dt.datetime.now(dt.timezone.utc)))
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None
    if out:
        os.makedirs(os.path.dirname(out), exist_ok=True); open(out, 'w').write(md); print('wrote', out)
    else:
        print(md)
