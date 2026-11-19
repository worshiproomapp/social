-- PROPOSAL (not applied). Move to migrations/ only when the attribution patch is approved.
-- Which social post sent a subscriber: the labels from the tracked link they arrived on. Nullable; old rows stay NULL.
ALTER TABLE subscribers ADD COLUMN utm_source   TEXT;
ALTER TABLE subscribers ADD COLUMN utm_medium   TEXT;
ALTER TABLE subscribers ADD COLUMN utm_campaign TEXT;
ALTER TABLE subscribers ADD COLUMN utm_content  TEXT;
ALTER TABLE subscribers ADD COLUMN utm_term     TEXT;
ALTER TABLE subscribers ADD COLUMN landing_path TEXT;  -- the page the tracked link opened

-- Aggregate landing counts for tracked links: a number per day and label set. No email, IP or identifier.
CREATE TABLE IF NOT EXISTS landings (
  day          TEXT    NOT NULL,
  path         TEXT    NOT NULL,
  utm_source   TEXT    NOT NULL,
  utm_medium   TEXT    NOT NULL DEFAULT '',
  utm_campaign TEXT    NOT NULL DEFAULT '',
  utm_content  TEXT    NOT NULL DEFAULT '',
  utm_term     TEXT    NOT NULL DEFAULT '',
  visits       INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (day, path, utm_source, utm_medium, utm_campaign, utm_content, utm_term)
);
