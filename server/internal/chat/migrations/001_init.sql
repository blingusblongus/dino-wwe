-- Chat messages, persisted across server restarts and used to backfill
-- late joiners + power the rewatch experience.

CREATE TABLE IF NOT EXISTS chat_messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    show_id    TEXT    NOT NULL,
    match_id   TEXT,                 -- null between matches
    round      INTEGER,              -- null if outside an active round
    user_id    TEXT    NOT NULL,     -- stable identity (auth uid OR anon cookie)
    handle     TEXT    NOT NULL,     -- display name shown to other users
    is_authed  INTEGER NOT NULL DEFAULT 0,  -- 0/1
    text       TEXT    NOT NULL,
    at_ms      INTEGER NOT NULL      -- unix milliseconds
);

CREATE INDEX IF NOT EXISTS idx_chat_show_at ON chat_messages(show_id, at_ms);
CREATE INDEX IF NOT EXISTS idx_chat_show_match ON chat_messages(show_id, match_id);

-- Show-level state (current match, current round) so the showrunner can
-- decorate incoming chat with timing context. Single-row-per-show.
CREATE TABLE IF NOT EXISTS show_state (
    show_id          TEXT PRIMARY KEY,
    current_match_id TEXT,
    current_round    INTEGER,
    updated_at_ms    INTEGER NOT NULL
);
