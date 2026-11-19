# Worship Room social: monthly pack runbook

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

## What a monthly pack contains (Free plan: max 10 queued posts per channel)

| Channel | Posts | Format | Default time (America/Chicago) |
|---|---|---|---|
| TikTok | 8 | vertical video, 1080×1920, 20–35 s | 2 per week, 7:30 PM (sleep/night topics 9:00 PM) |
| Instagram | 8 | 4 Reels (reuse 4 of the TikTok videos, 2+ days after their TikTok date) + 4 feed images 1080×1350 | 2 per week, 12:00 PM |
| Pinterest | 8 | pins 1000×1500 | 2 per week, 8:00 PM |

Total new assets: 8 videos, 4 Instagram images, 8 pins. Spread posts across the whole month, days 1–28.
Before scheduling, count each channel's already-queued posts with `list_posts` (status scheduled); never exceed 10 per channel.

## Writing the pack (`content/packs/YYYY-MM.json`; copy the shape of the latest pack)

- Every post links to one guide from `content/guides.json` (the check enforces this). Rotate topics; don't repeat a passage used in the previous 3 packs.
- Topic mix each month: anxiety/fear/peace, grief/loneliness/healing (gentle), hope/strength/encouragement, God's love, prayer how-tos (how to pray, morning prayer, the Lord's Prayer, prayer journal, can't sleep), Bible reading (in a year, where to start, printable plans), Psalm 23/91, Jeremiah 29:11. Fit the season (Advent and Christmas in December, new-year reading plans in January, Easter in spring), but link to an existing guide.
- Design (template 2, set `"template": 2` in every pack): posts use the homepage's "Room in the Margin" look, built by `tools/render.py` from the app's own pieces: the hero galaxy (`assets/bg/`, rendered from the app's galaxy engine), the Parchment leaf with deckled edges and paper grain, Lora display type with one italic emphasis and a hand-drawn First Light underline, small tracked labels, the "Go deeper:" link line, and the script wordmark. Copy the field shape from `content/examples/template-v2.json`. Don't add new visual elements (no emoji, icons, gradients, stock photos, or AI imagery); the restraint is the brand.
- Videos: `kicker` (short label, e.g. "When you can't sleep"), `hook` (shown big on frame 0; a short, plain question or promise) with `hook_em` (the one word or phrase in it that gets italic + the underline), optional `leadin` (an italic line on the paper, e.g. "For a mind that won't settle, a word to rest on:"), `pages` (verse chunks of ≤ ~24 characters each, one per line; optional prayer page with `"style": "prayer"` and a `label` such as "A prayer for tonight"), `go_deeper` (the guide's name as people would search it), and `music`: D (warm), F (slow night: sleep, grief), or G (open, hopeful). Aim for 20–30 seconds: one verse page, plus a prayer page only when the topic is prayer. Prayers must be Worship Room's own words (short, humble, no promises).
- Images (Instagram 1080×1350, Pinterest 1000×1500): `kicker`, `headline` (for pins, the search query itself, e.g. "What to pray when you can't sleep.") with `headline_em`, optional `leadin`, `quote` + `ref` + `verify`, `go_deeper`, and `bg` (14000, 26000 or 38000: rotate the three galaxy stills). Keep quotes to ~45 words or fewer; use `size` to shrink the verse only when needed.
- Captions: open with the question people actually search ("What does the Bible say about…?", "What to pray when…"), include the passage text, one or two sentences of reflection, "from Worship Room:" plus the guide path, and 3–4 relevant hashtags. Pinterest gets a keyword title (the search query), a description, alt text, and a board: "Prayers", "Bible Verses for Hard Days", or "Bible Study & Reading Plans".
- Alt text describes the image literally: background, heading, the full quote with reference, the footer, "Worship Room, worshiproom.com."

## Monthly run (what the scheduled task does)

1. Attach and clone this repo (push access), `pip install --break-system-packages --no-deps tinysoundfont`, and confirm `ffmpeg`, Playwright, and Chrome/Chromium are available.
2. Buffer: `get_account` → organization; `list_channels`; `get_channel` on Pinterest for board IDs; `list_posts` (scheduled) for queue counts; `list_posts` with `includeMetrics` for last month's posts. Note what did best (watch time, reach, saves) and lean the new pack that way.
3. Write `content/packs/<month>.json`, then `python3 tools/build.py content/packs/<month>.json --check` until it passes.
4. `python3 tools/build.py content/packs/<month>.json` renders `media/<month>/` and `build/<month>/` (`schedule.json` plus a `preview/` page).
5. Look at the output yourself before anyone else does: Read every PNG, and pull 3–4 frames from every video with ffmpeg. Fix wrapping, crowding, or anything off-brand, then rebuild.
6. Commit `media/<month>/` and the pack JSON, then push to main. Pages updates within a minute or two.
7. Publish `build/<month>/preview/` as an artifact titled "Worship Room social: <Month YYYY> pack" (publish_files).
8. Schedule every post from `build/<month>/schedule.json` with Buffer `create_post` (mode customScheduled, schedulingType automatic):
   - TikTok: text = caption; video asset with `thumbnailOffset` = `thumbnail_ms`.
   - Instagram Reel: `metadata.instagram = {type: "reel", shouldShareToFeed: true}`. Feed image: `{type: "post", shouldShareToFeed: true}` with image `altText`.
   - Pinterest: `metadata.pinterest = {boardServiceId, title, url: link}`; text = caption; image `altText`.
   - If Buffer rejects a media URL right after the push, wait two minutes (Pages deploy) and retry once.
9. Send the owner a push notification and a short summary: the preview link, the post count per channel, the first post date, and how to pull a post ("reply 'pull #N'").

Old months' media must stay in `media/` until every post that uses it has published.
