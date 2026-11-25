# Worship Room social: weekly pack runbook

This repo holds the tools, assets, and published media for Worship Room's scheduled social posts.
Media under `media/` is served by GitHub Pages at `https://worshiproomapp.github.io/social/media/...`,
and Buffer fetches it from there. Use American spelling in everything.

## The brand (non-negotiable)

- Speak only as "Worship Room." Organizational and anonymous: never a founder name, face, or founder story.
- Canonical sentence (use verbatim when describing the app): "Worship Room is an ad-free Christian web app for emotional healing and worship — free to start, with daily devotionals, a Bible reader, reading plans, journaling, an AI Bible guide, a community prayer wall, and worship music."
- Status: pre-launch, opening mid-2027.
- Pricing is "free to start," never a blanket "free." A free printable PDF can be called free.
- Never mention Challenges, Meditate, Local Support (churches, counselors, Celebrate Recovery), "prayer AI," or friends/messaging.
- Never imply counseling, therapy, crisis help, or medical advice. On anxiety, grief, sleep, and health, stay gentle and spiritual and make no promises. If a post touches real distress, it may add: "If you're in crisis, call or text 988." Keep the not-a-substitute-for-care posture.
- Calm, sincere tone. No hype. At most one exclamation point per post (prefer none).
- Public email: contact@worshiproom.com only.

## Scripture

- Quote the World English Bible (WEB) wording exactly, with the reference only. Never print a translation label.
- Check any passage with `python3 tools/web.py PSA:23:1-3` (USFX book codes: GEN, EXO, ... PSA, PRO, ISA, JER, LAM, MAT, MRK, LUK, JHN, ROM, 1CO, 2CO, GAL, EPH, PHP, COL, HEB, JAS, 1PE, 1JN, REV).
- `tools/build.py --check` verifies every video and image passage against the WEB text and every quoted string of 6+ words in captions, alt text, and titles. A pack never ships with a failing check.
- Keep the WEB wording even where it reads unusually (for example "Yahweh").

## Cadence: a weekly pack, as much as Buffer Free holds

Buffer Free allows 10 queued posts per channel at any time. Packs are built every Wednesday for the Monday–Sunday week that
starts 5 days later (the owner's review window: he can reply "pull #N"). At build time the queue holds the rest of the current
week plus the new week, about 12 days, so the ceiling is **5 posts per channel per week** (~8–9 queued). `tools/build.py --check`
enforces 5 per channel per ISO week, counting posts already committed in `content/schedules/`, and the same guide on the same
channel at most once per 14 days. Before scheduling, count each channel's queued posts with `list_posts` (status scheduled);
never exceed 10. If the cap is tight (for example while an older monthly pack is still draining), schedule fewer posts, never more.

| Channel | Target per week | Format | Default time (America/Chicago) |
|---|---|---|---|
| TikTok | 5 | ~4 vertical videos 1080×1920, 15–30 s + ~1 photo-mode carousel (1080×1920) | 7:30 PM (sleep/night topics 9:00 PM) |
| Instagram | 5 | ~3 Reels (reused TikTok videos, 2+ days after their TikTok date) + ~2 feed posts: carousels and single images 1080×1350 | 12:00 PM |
| Pinterest | 5 | fresh pins 1000×1500 (single image), each to a different guide | 8:00 PM |

Spread posts across the week (no two on the same channel on the same day). 5 is a ceiling, not a quota: a pack that can't
meet the quality bar ships fewer posts. Never pad with filler, near-duplicates, or a recycled image with a new caption
(a fresh pin for a guide pinned 14+ days ago needs a new image, angle and title).

Naming: the pack id is the ISO week of its posts, e.g. `2026-W50`: `content/packs/2026-W50.json` (`"pack": "2026-W50"`),
`media/2026-W50/`, `previews/2026-W50/`, `content/schedules/2026-W50.json`, post ids `2026-W50-tt-01`.
Older monthly packs (`2026-11`, `2026-12`) keep their names.

## Strategy and measurement (read before writing a pack)

- `content/strategy.md`: purposes, funnel, UTM scheme, platform playbook, content pillars, running experiments, decision rules.
- `content/insights.md`: dated observations and hypotheses with denominators. Only `tools/analyze.py` FINDINGS change strategy.
- `content/guides-text/<slug>.txt`: the text of each guide. Context lines, answers and carousel text must come from here.
- `content/schedules/<pack>.json` (written by the build, committed): post ids, purposes, experiments and media URLs, used by `tools/analyze.py`.

## Writing the pack (`content/packs/<pack>.json`; copy the shape of `content/examples/template-v3.json`)

- Template 3 (set `"template": 3`): every post has a unique `id` (`<pack>-<tt|ig|pin>-<nn>`, it becomes `utm_content`), a `purpose`
  (`discover`, `save` or `visit`) and, when it is part of a test, an `experiment` `{name, arm}` declared in the pack's `experiments`
  (hypothesis, metric, arms, min_per_arm). Carry running experiments from `content/strategy.md`; one variable at a time.
- Carousels (`carousels`): cover → 3–6 content slides (verse with a context note, or a plain-answer text slide) → end card. Every
  sentence of a note or answer must come from the linked guide's text (the check enforces this). Pinterest never gets a carousel.
- Videos may add an `"answer"` page (a plain answer from the guide; set the video's `link`) and `"pace": "fast"` for the fast arm of `tt-pace`.
- Pinterest pin URLs use the tracked link the build writes (`tracked_link`). TikTok and Instagram captions keep the clean path.

- Every post links to one guide from `content/guides.json` (the check enforces this). Rotate topics; don't repeat a passage used in the previous 6 weeks on any channel (check content/packs/).
- Topic mix across each month (about 20 posts per channel): anxiety/fear/peace, grief/loneliness/healing (gentle), hope/strength/encouragement, God's love, prayer how-tos (how to pray, morning prayer, the Lord's Prayer, prayer journal, can't sleep), Bible reading (in a year, where to start, printable plans), Psalm 23/91, Jeremiah 29:11. Fit the season (Advent and Christmas in December, new-year reading plans in January, Easter in spring), but link to an existing guide.
- Design: posts use the homepage's "Room in the Margin" look, built by `tools/render.py` from the app's own pieces: the hero galaxy (`assets/bg/`, rendered from the app's galaxy engine), the Parchment leaf with deckled edges and paper grain, Lora display type with one italic emphasis and a hand-drawn First Light underline, small tracked labels, the "Go deeper:" link line, and the script wordmark. Copy the field shape from `content/examples/template-v2.json`. Don't add new visual elements (no emoji, icons, gradients, stock photos, or AI imagery); the restraint is the brand.
- Videos: `kicker` (short label, e.g. "When you can't sleep"), `hook` (shown big on frame 0; a short, plain question or promise) with `hook_em` (the one word or phrase in it that gets italic + the underline), optional `leadin` (an italic line on the paper, e.g. "For a mind that won't settle, a word to rest on:"), `pages` (verse chunks of ≤ ~24 characters each, one per line; optional prayer page with `"style": "prayer"` and a `label` such as "A prayer for tonight"), `go_deeper` (the guide's name as people would search it), and `music`: D (warm), F (slow night: sleep, grief), or G (open, hopeful). Aim for 20–30 seconds: one verse page, plus a prayer page only when the topic is prayer. Prayers must be Worship Room's own words (short, humble, no promises).
- Images (Instagram 1080×1350, Pinterest 1000×1500): `kicker`, `headline` (for pins, the search query itself, e.g. "What to pray when you can't sleep.") with `headline_em`, optional `leadin`, `quote` + `ref` + `verify`, `go_deeper`, and `bg` (14000, 26000 or 38000: rotate the three galaxy stills). Keep quotes to ~45 words or fewer; use `size` to shrink the verse only when needed.
- Captions: open with the question people actually search ("What does the Bible say about…?", "What to pray when…"), include the passage text, one or two sentences of reflection, "from Worship Room:" plus the guide path, and 3–4 relevant hashtags. Pinterest gets a keyword title (the search query), a description, alt text, and a board: "Prayers", "Bible Verses for Hard Days", or "Bible Study & Reading Plans".
- Alt text describes the image literally: background, heading, the full quote with reference, the footer, "Worship Room, worshiproom.com."

## Weekly run (what the scheduled task does)

1. Attach and clone this repo (push access), `pip install --break-system-packages --no-deps tinysoundfont`, and confirm `ffmpeg`, Playwright, and Chrome/Chromium are available.
2. Buffer: `get_account` → organization; `list_channels`; `get_channel` on Pinterest for board IDs; `list_posts` (scheduled) for queue counts; `list_posts` with `includeMetrics` (status sent) for the last ~8 weeks, saved to `metrics/<date>.json`, then `python3 tools/analyze.py metrics/<date>.json --out content/reports/<date>.md`. Apply FINDINGS; treat everything else as a hypothesis to test, not a rule.
3. Write `content/packs/<pack>.json`, then `python3 tools/build.py content/packs/<pack>.json --check` until it passes.
4. `python3 tools/build.py content/packs/<pack>.json` renders `media/<pack>/`, `previews/<pack>/index.html`, `content/schedules/<pack>.json` and `build/<pack>/schedule.json`.
5. Look at the output yourself before anyone else does: Read every PNG, and pull 3–4 frames from every video with ffmpeg. Fix wrapping, crowding, or anything off-brand, then rebuild.
6. Commit `media/<pack>/`, `previews/<pack>/`, `content/schedules/<pack>.json`, the pack JSON and any report, then push to main. Pages updates within a minute or two.
7. The preview is `https://worshiproomapp.github.io/social/previews/<pack>/` (noindex, and robots.txt disallows the site).
8. Schedule every post from `build/<pack>/schedule.json` with Buffer `create_post` (mode customScheduled, schedulingType automatic):
   - TikTok: text = caption; video asset with `thumbnailOffset` = `thumbnail_ms`. Photo carousel: the `images` list in order, each with its `alt` as `altText`.
   - Instagram Reel: `metadata.instagram = {type: "reel", shouldShareToFeed: true}`. Feed image: `{type: "post", shouldShareToFeed: true}` with image `altText`. Carousel: `{type: "post"}` with every slide image in order, each with its `altText`.
   - Pinterest: `metadata.pinterest = {boardServiceId, title, url: tracked_link}`; text = caption; image `altText`.
   - If Buffer rejects a media URL right after the push, wait two minutes (Pages deploy) and retry once.
9. End with the short summary the scheduled task prompt describes (its push notification delivers it): preview link, counts per channel, first post date (5+ days out), experiments, and how to pull a post ("reply 'pull #N'").

Older packs' media must stay in `media/` until every post that uses it has published.
