# Worship Room social strategy

Owner of this file: the monthly pack task (it reads it before writing a pack) and the twice-monthly health check (it updates
"What we know" only when `tools/analyze.py` labels something a FINDING). Last full review: 2026-11-19.

## The job of social before launch

Worship Room opens mid-2027. Until then every post has one of three purposes, and the pack names it on each post (`purpose`):

| Purpose | What success looks like | Primary metric (with its denominator) |
|---|---|---|
| `discover` | New people see it and watch or read to the end | TikTok/IG: average watch % of length, reach; Pinterest: impressions |
| `save` | People keep it for a hard day | saves per 100 reach (per 1,000 impressions on Pinterest) |
| `visit` | People go to the guide, then join the list | Pinterest outbound clicks; site visits and signups by guide path |

## The funnel and where each step is measured

| Step | Measured by | Available today? |
|---|---|---|
| Impression / reach | Buffer metrics per post | Yes |
| Engagement (watch time, saves, shares, comments) | Buffer metrics per post | Yes. No retention curve. |
| Profile visit / link-in-bio tap | TikTok and Instagram native analytics | Owner only; not in Buffer |
| Outbound click | Pinterest native analytics | Owner only; Buffer "Pin Clicks" are closeups, not link clicks |
| Website visit | Cloudflare Web Analytics on worshiproom.com (path, referrer host, country) | Yes, owner dashboard. As far as we could verify, it does not report UTM parameters. |
| Guide engagement | Same, by guide path | Yes, page views only |
| Waitlist signup | D1 `subscribers.source` = `coming-soon:<path>` | Yes, by page. Not by platform or post. |

The gap: nothing today connects a signup to the platform or post that sent the person. The fix is drafted, not deployed
(see "Website attribution" below).

## Tracked links (UTM)

Every clickable destination carries:

```
utm_source=<tiktok|instagram|pinterest>&utm_medium=social&utm_campaign=<YYYY-MM>-pack&utm_content=<post id>&utm_term=<guide slug>
```

- Post ids are `<YYYY-MM>-<tt|ig|pin>-<nn>` and are unique within a pack. `tools/build.py` writes the tracked link per post.
- Pinterest pins use the tracked link as the pin URL (every pin is clickable).
- TikTok and Instagram captions are not clickable, so captions keep the clean path (worshiproom.com/guides/...). Tracking those
  platforms happens through the bio link.
- Bio links (owner sets these once):
  - Instagram: `https://worshiproom.com/?utm_source=instagram&utm_medium=social&utm_campaign=profile&utm_content=bio`
  - TikTok (if the profile link field is available): `https://worshiproom.com/?utm_source=tiktok&utm_medium=social&utm_campaign=profile&utm_content=bio`
  - Pinterest profile website: `https://worshiproom.com/?utm_source=pinterest&utm_medium=social&utm_campaign=profile&utm_content=bio`
- Until the website attribution patch ships, UTMs are recorded nowhere; they are harmless, and they start counting the day it ships.

## Website attribution (drafted, owner approval needed)

`proposals/attribution/` in the coming-soon folder: cookieless first-touch capture of the UTM fields in sessionStorage,
sent with the signup and stored in new D1 columns, plus the privacy policy sentence that has to change with it.
Not deployed. Until it is, platform-level traffic comes from Cloudflare's referrer report (pinterest.com,
tiktok.com, instagram.com / l.instagram.com) and guide-level signups from `npm run list:count` / D1 `source`.

## Formats and platforms

**TikTok** (8 a month): the hook decides everything. Test batch: average watch 2.2s and 3.0s on 30.5s and 37.4s videos (two posts:
a hypothesis, not a finding). Frame 0 shows a plain question people search, in big type. Videos stay 15–30s. Two of the eight are
photo-mode carousels (1080×1920, swipeable). Default 7:30 PM, sleep and night topics 9:00 PM.

**Instagram** (8 a month): 4 Reels (reused TikTok videos, 2+ days later) for reach; the other 4 are save-worthy feed posts:
carousels (1080×1350, 5–7 slides: a question, Scripture with a line of context from our guide, a practical step, the end card)
and single verse images while the format experiment runs.

**Pinterest** (8 a month): Pinterest is a search engine. The title is the search query; the description answers it; the pin links
to the guide that answers it fully. Pins take weeks to months to distribute: judge a pin no earlier than 30 days, and prefer
90-day reads. Fresh pins on the same guide (new image, new title angle) are how Pinterest wants repeat topics.

**Backlog:** five prayer pins (healing, how to pray, strength, grief, guidance) were scheduled in Chrome before Buffer and never
published. Their topics go to the front of the Pinterest queue, re-rendered in the current look.

## Content pillars (every post fits one)

1. **Prayers for a moment** (anxiety, can't sleep, grief, strength, guidance, healing, morning). Short, humble prayers in our own words.
2. **Scripture with context** (Psalm 23, Psalm 91, Jeremiah 29:11, Philippians 4:6-7). The verse, plus one sentence of context taken from our guide.
3. **Real questions, plain answers** ("Is it a sin to feel anxious?", "Where should I start reading the Bible?"). Answers come from the
   guide text; `build.py` fails a carousel slide or answer page whose sentences are not in the linked guide.
4. **Bible reading help** (in a year, where to start, the printable plan). The printable plan is the best Pinterest performer so far (26 impressions; small).

## Experiments

One variable at a time. Each has a hypothesis, a metric with its denominator, arms, and a minimum posts per arm (usually 4).
An experiment can run across two packs. Results are FINDINGS only when `tools/analyze.py` says so.

Running from December 2026:

| Name | Hypothesis | Metric | Arms | Judged at |
|---|---|---|---|---|
| `tt-pace` | A 1.5s hook and quicker reveals (15–20s videos) hold a bigger share of the video than the standard pace | avg watch % of length | standard, fast | 4 per arm (Jan) |
| `ig-feed-format` | Carousels earn more saves than single verse images | saves per 100 reach | carousel, image | 4 per arm (Jan) |
| `tt-format` | Photo-mode carousels reach as many people as videos on a new account | reach per post, saves per 100 reach | video, photo | 4 photo posts (Feb) |

## What we know (FINDINGS only)

None yet. Six test posts and 20 early pins are below every threshold. See `content/insights.md` for observations and hypotheses.

## Decision rules for the health check

- **Fix automatically:** a post in `error`, a media URL that fails, a broken or wrong link, a typo or rule break in a queued caption.
- **Never automatically:** move, rewrite, or delete a queued post because of weak or early numbers.
- **Strategy changes:** only on a FINDING, and they apply to the next pack (written into this file), not to the queue.
