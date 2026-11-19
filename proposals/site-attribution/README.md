# Proposal: know which social post brought each visit and signup

> Kept in the social repo because it only matters for social attribution. It applies to the coming-soon site
> (`~/worshiproom-coming-soon`), which is not under Git. Optional: nothing in the social pipeline depends on it.

Status: NOT deployed. Nothing in this folder is used by `npm run deploy` (the deploy uses `public/`, `src/` and `migrations/` only).

## Why

Today you can see visits by page and referrer (Cloudflare Web Analytics) and signups by page (`subscribers.source`).
You cannot see which platform or post sent a signup. Social links now carry labels like
`?utm_source=pinterest&utm_medium=social&utm_campaign=2026-12-pack&utm_content=2026-12-pin-03&utm_term=prayer-for-grief`.
Cloudflare Web Analytics does not record query strings at all (its official FAQ: "Does Cloudflare Web Analytics support UTM
parameters? Not yet."), so it shows the page path and the referring site but never these labels. The site records them itself.

## What it changes

1. `public/app.js`: when a page opens from a tracked link, it keeps the labels and the page that opened in sessionStorage
   (this tab only, no cookie), removes them from the address bar, and sends them with the signup. The first tracked link in a
   tab wins. It also adds one to a daily count for that link.
2. `src/worker.js`: stores the labels and landing page with the signup (new nullable columns) and keeps the daily counts (`/api/landing`).
   Only short lowercase labels are accepted; anything else is dropped.
3. `migrations/0002_add_attribution.sql` (this folder's copy): the new columns and the `landings` table.
4. `public/privacy-policy.html`: the "what we collect" list says so. This change ships in the same deploy, never later.
5. `package.json`: `npm run list:sources` (signups by platform, page and post) and `npm run list:landings` (tracked visits).

No email, IP address, name, cookie or device identifier is added anywhere.

## What each signup row will say

| Arrived through | utm_source | utm_content | landing_path | source (signup page) |
|---|---|---|---|---|
| A pin | pinterest | the pin's post id, e.g. 2026-12-pin-03 | the guide the pin opened | the page they joined on |
| Instagram or TikTok bio link | instagram / tiktok | bio | / | the page they joined on |
| Anything else (search, typed, a shared link) | null | null | null | the page they joined on |

Instagram and TikTok captions are not clickable, so their signups are attributed to the platform, not to a post.

## Limits (by design: no cookies, nothing about the person)

- Attribution lasts for the browser tab. Someone who leaves and comes back later, or opens the site in a new tab or another
  app (for example, copies the link out of Instagram's in-app browser into Safari), is not attributed.
- The landing counter can be inflated by anyone who calls `/api/landing`; read it as directional.

## Tested (locally, nothing deployed)

`e2e_test.py` runs against `wrangler dev --local` with this patch and migration applied and a stubbed Turnstile. 12/12 passed
on 2026-11-19: tracked pin → two guide-to-guide navigations → reload → signup stores platform, medium, campaign, post, guide,
landing page and signup page; first touch wins; untracked signups store nulls; the bio link stores platform + "bio"; a fresh
tab has no attribution; junk labels are dropped; one landing count per tracked landing; no cookie is set.

## To ship it (about 10 minutes)

1. In Terminal: `cd ~/worshiproom-coming-soon`
2. Back up, then apply the patch: `mkdir -p /tmp/wr-backup && cp -R public src package.json /tmp/wr-backup/`
   then `patch -p1 < proposals/site-attribution/attribution.patch`
3. Move the migration in: `cp proposals/site-attribution/0002_add_attribution.sql migrations/`
4. Apply it to the live database: `npm run db:migrate` (it asks to confirm; answer yes).
5. Deploy: `npm run deploy`
6. Test: open `https://worshiproom.com/guides/how-to-pray?utm_source=test&utm_content=check` in a private window. The address bar
   should drop the `?utm_…` part. Then run `npm run list:landings`: a `test` row with 1 visit should appear.
7. Tell Claude it's live.

To skip the landing counter and keep only signup attribution: before step 2, remove the `navigator.sendBeacon` line from the patch.

## Undo

`patch -R -p1 < proposals/site-attribution/attribution.patch`, then `npm run deploy`. The extra columns and table can stay; they are unused.
