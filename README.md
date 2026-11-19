# Worship Room social media assets

Media and tooling for Worship Room's scheduled social posts. Media is served with GitHub Pages so the scheduler can fetch it.

- `media/YYYY-MM/`: videos and images for that month's posts
- `content/packs/YYYY-MM.json`: the month's verses, captions, alt text, and schedule
- `content/guides.json`: guides that posts link to
- `tools/`: `build.py` checks a pack (Scripture wording, links, content rules) and renders it; `web.py` looks up passages
- `assets/`: fonts (SIL Open Font License), World English Bible text (public domain), GeneralUser GS SoundFont (see its license)

Music in the videos is original, composed and rendered by `tools/music.py`.

Learn more at https://worshiproom.com
