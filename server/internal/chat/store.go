// Package chat owns SQLite persistence for chat messages and show timing state.
package chat

import (
	"context"
	"database/sql"
	"embed"
	"fmt"
	"sort"
	"strings"
	"time"

	_ "modernc.org/sqlite"
)

//go:embed migrations/*.sql
var migrationsFS embed.FS

type Message struct {
	ID       int64  `json:"id"`
	ShowID   string `json:"show_id"`
	MatchID  string `json:"match_id,omitempty"`
	Round    int    `json:"round,omitempty"`
	UserID   string `json:"user_id"`
	Handle   string `json:"handle"`
	IsAuthed bool   `json:"is_authed"`
	Text     string `json:"text"`
	AtMs     int64  `json:"at_ms"`
}

type ShowState struct {
	ShowID         string
	CurrentMatchID string
	CurrentRound   int
}

type Store struct {
	db *sql.DB
}

// NewStore opens (creating if needed) the SQLite file at path and applies
// embedded migrations in lexical order. WAL mode for better concurrency.
func NewStore(path string) (*Store, error) {
	dsn := fmt.Sprintf("file:%s?_pragma=journal_mode(WAL)&_pragma=busy_timeout(5000)&_pragma=foreign_keys(1)", path)
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("ping: %w", err)
	}
	s := &Store{db: db}
	if err := s.migrate(); err != nil {
		_ = db.Close()
		return nil, err
	}
	return s, nil
}

func (s *Store) Close() error { return s.db.Close() }

func (s *Store) migrate() error {
	entries, err := migrationsFS.ReadDir("migrations")
	if err != nil {
		return fmt.Errorf("read embedded migrations: %w", err)
	}
	names := make([]string, 0, len(entries))
	for _, e := range entries {
		if !e.IsDir() && strings.HasSuffix(e.Name(), ".sql") {
			names = append(names, e.Name())
		}
	}
	sort.Strings(names)
	for _, name := range names {
		body, err := migrationsFS.ReadFile("migrations/" + name)
		if err != nil {
			return fmt.Errorf("read %s: %w", name, err)
		}
		if _, err := s.db.Exec(string(body)); err != nil {
			return fmt.Errorf("apply %s: %w", name, err)
		}
	}
	return nil
}

// Save inserts a message and returns it with ID populated.
func (s *Store) Save(ctx context.Context, m Message) (Message, error) {
	if m.AtMs == 0 {
		m.AtMs = time.Now().UnixMilli()
	}
	authed := 0
	if m.IsAuthed {
		authed = 1
	}
	res, err := s.db.ExecContext(ctx, `
		INSERT INTO chat_messages
		    (show_id, match_id, round, user_id, handle, is_authed, text, at_ms)
		VALUES (?, NULLIF(?, ''), NULLIF(?, 0), ?, ?, ?, ?, ?)
	`, m.ShowID, m.MatchID, m.Round, m.UserID, m.Handle, authed, m.Text, m.AtMs)
	if err != nil {
		return m, fmt.Errorf("insert message: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return m, fmt.Errorf("last id: %w", err)
	}
	m.ID = id
	return m, nil
}

// Backfill returns the most recent `limit` messages for a show, ordered oldest-first.
func (s *Store) Backfill(ctx context.Context, showID string, limit int) ([]Message, error) {
	if limit <= 0 {
		limit = 100
	}
	rows, err := s.db.QueryContext(ctx, `
		SELECT id, show_id, COALESCE(match_id, ''), COALESCE(round, 0),
		       user_id, handle, is_authed, text, at_ms
		FROM (
		    SELECT * FROM chat_messages WHERE show_id = ? ORDER BY id DESC LIMIT ?
		) ORDER BY id ASC
	`, showID, limit)
	if err != nil {
		return nil, fmt.Errorf("backfill query: %w", err)
	}
	defer rows.Close()

	var out []Message
	for rows.Next() {
		var m Message
		var authed int
		if err := rows.Scan(&m.ID, &m.ShowID, &m.MatchID, &m.Round, &m.UserID, &m.Handle, &authed, &m.Text, &m.AtMs); err != nil {
			return nil, fmt.Errorf("scan: %w", err)
		}
		m.IsAuthed = authed == 1
		out = append(out, m)
	}
	return out, rows.Err()
}

// CurrentState fetches the show's current match/round, or zero-value if unset.
func (s *Store) CurrentState(ctx context.Context, showID string) (ShowState, error) {
	row := s.db.QueryRowContext(ctx, `
		SELECT show_id, COALESCE(current_match_id, ''), COALESCE(current_round, 0)
		FROM show_state WHERE show_id = ?
	`, showID)
	var st ShowState
	err := row.Scan(&st.ShowID, &st.CurrentMatchID, &st.CurrentRound)
	if err == sql.ErrNoRows {
		return ShowState{ShowID: showID}, nil
	}
	if err != nil {
		return st, fmt.Errorf("scan show state: %w", err)
	}
	return st, nil
}

// SetState upserts the show's current match/round.
func (s *Store) SetState(ctx context.Context, st ShowState) error {
	_, err := s.db.ExecContext(ctx, `
		INSERT INTO show_state (show_id, current_match_id, current_round, updated_at_ms)
		VALUES (?, NULLIF(?, ''), NULLIF(?, 0), ?)
		ON CONFLICT(show_id) DO UPDATE SET
		    current_match_id = excluded.current_match_id,
		    current_round    = excluded.current_round,
		    updated_at_ms    = excluded.updated_at_ms
	`, st.ShowID, st.CurrentMatchID, st.CurrentRound, time.Now().UnixMilli())
	return err
}
