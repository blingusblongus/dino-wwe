-- Persisted show events (vignettes, match rounds, etc.) so late joiners
-- and page refreshes can see everything from the start of the show.

CREATE TABLE IF NOT EXISTS show_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    show_id    TEXT    NOT NULL,
    kind       TEXT    NOT NULL,     -- "vignette.drop", "match.start", "match.round", "match.end"
    payload    TEXT    NOT NULL,     -- raw JSON payload
    fired_at   INTEGER NOT NULL     -- unix milliseconds when the showrunner fired it
);

CREATE INDEX IF NOT EXISTS idx_show_events_show ON show_events(show_id, id);
