# Performance insights

Observations and hypotheses, each with its denominator. Nothing here is a FINDING (see content/strategy.md for the rules);
the monthly pack treats these as things to test, not rules.

## 2026-11-19 audit (test batch: 6 Buffer posts Nov 13–18, plus 20 pins scheduled from Nov 10)
- Setup verified: TikTok auto-publish, Instagram Reel + feed image with alt text, and Pinterest board/title/link/alt all work
  through Buffer from GitHub Pages URLs.
- TikTok (2 videos): reach 132 and 130; average watch 2.2 s of 30.5 s and 3.0 s of 37.4 s (about 7–8% of the length).
  Hypothesis: viewers leave before the verse appears. The hook on frame 0 shipped in template 2; the December `tt-pace`
  experiment tests a faster version.
- TikTok engagement: 1 like / 132 reach vs 6 likes + 1 share / 130 reach. The second was the "for tonight" sleep prayer.
  Hypothesis: personal, moment-specific prayers engage more than a verse alone. One pair of posts; test more.
- Instagram Reel (Psalm 23): 100 reach, 6 likes, 1 comment, 0 saves, 0 shares; average watch 3.4 s of 29.3 s.
- Instagram feed image (Isaiah 41:10): 0 reach after 2 days on a 0-follower account. Hypothesis: single images get no
  distribution without followers. One post; the `ig-feed-format` experiment tests carousels against images.
- Pinterest (Buffer pins): 0 impressions after 1–3 days. Normal; judge pins at 30+ days.
- Pinterest (all pins since Nov 10): 131 impressions, 2 closeups, 0 saves across 20 pins. Best single pin: the printable
  reading plan (26 impressions). Too early to judge.
- TikTok strips caption line breaks. Keep TikTok captions as short paragraphs that read fine run together. (Observed, not a metric.)

## 2026-11-24 (monthly pack run; report: content/reports/2026-11-24.md)
- No FINDINGS. Every comparison is below the 4-posts / 300-reach rule.
- TikTok average watch, corrected: 2.06 s (Philippians 4:6–7, 132 reach) and 3.02 s (Psalm 4:8 sleep prayer, 132 reach).
  The analyzer had been reading total time watched (5.08 s, 7.3 s) as the average, and could not join TikTok posts to the
  pack because Buffer re-hosts the video; both fixed in tools/analyze.py (exact `averageTimeWatched`, join by channel + time).
- Instagram: Psalm 23 Reel 100 reach, 6 likes, 1 comment, 0 saves; average watch 3.67 s. Both feed images: 0 reach.
- Pinterest: 22 pins, all under 30 days old (too early). The Nov 10 pins hold 4–41 impressions each; 2 closeups, 0 saves.
