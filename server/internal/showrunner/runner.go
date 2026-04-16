// Package showrunner walks a show's runsheet and broadcasts the events at
// their scheduled times.
//
// One goroutine per show. Past events fire immediately (catch-up); future
// events sleep until their `at` time. Show state (current match/round) is
// upserted into SQLite as match.* events fire so chat messages can be
// tagged with timing context.
package showrunner

import (
	"context"
	"encoding/json"
	"log"
	"os"
	"path/filepath"
	"sort"
	"time"

	"github.com/nallen/dino-wwe/server/internal/chat"
)

// EventKind identifies what action the showrunner should take at an event's
// scheduled time. These are also the wire `type` values the hub broadcasts.
type EventKind string

const (
	KindMatchStart   EventKind = "match.start"
	KindMatchRound   EventKind = "match.round"
	KindMatchEnd     EventKind = "match.end"
	KindVignetteDrop EventKind = "vignette.drop"
)

// Event is one entry in a runsheet. Payload is held as raw JSON so the
// showrunner can pass it through to broadcast without re-serializing.
type Event struct {
	At      time.Time       `json:"at"`
	Kind    EventKind       `json:"kind"`
	Payload json.RawMessage `json:"payload,omitempty"`
}

// Runsheet is the canonical record of a show's wall-clock schedule.
type Runsheet struct {
	ShowID   string    `json:"show_id"`
	Title    string    `json:"title"`
	StartsAt time.Time `json:"starts_at"`
	Events   []Event   `json:"events"`
}

// Hub is the minimal surface the showrunner needs from ws.Hub. Defining it
// as an interface keeps the import graph clean and lets us mock it.
type Hub interface {
	Broadcast(showID, kind string, payload any)
}

// Runner discovers runsheets under <data>/shows/*/runsheet.json and walks
// each one in its own goroutine.
type Runner struct {
	dataDir string
	hub     Hub
	store   *chat.Store
}

func New(dataDir string, hub Hub, store *chat.Store) *Runner {
	return &Runner{dataDir: dataDir, hub: hub, store: store}
}

// Start scans for runsheets and launches a goroutine per show.
func (r *Runner) Start(ctx context.Context) {
	dir := filepath.Join(r.dataDir, "shows")
	entries, err := os.ReadDir(dir)
	if err != nil {
		if os.IsNotExist(err) {
			log.Printf("showrunner: %s does not exist yet — no shows to walk", dir)
			return
		}
		log.Printf("showrunner: read %s: %v", dir, err)
		return
	}
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		path := filepath.Join(dir, e.Name(), "runsheet.json")
		rs, err := LoadRunsheet(path)
		if err != nil {
			log.Printf("showrunner: load %s: %v", path, err)
			continue
		}
		log.Printf("showrunner: starting walk show=%s title=%q events=%d starts_at=%s",
			rs.ShowID, rs.Title, len(rs.Events), rs.StartsAt.Format(time.RFC3339))
		go r.walk(ctx, rs)
	}
}

// walk fires every event in the runsheet on schedule. Past events fire
// immediately. Future events sleep until their `at`.
func (r *Runner) walk(ctx context.Context, rs Runsheet) {
	defer log.Printf("showrunner[%s]: walk complete", rs.ShowID)

	for i, ev := range rs.Events {
		wait := time.Until(ev.At)
		if wait > 0 {
			select {
			case <-ctx.Done():
				return
			case <-time.After(wait):
			}
		}
		r.fire(ctx, rs.ShowID, i, ev)
	}
}

// fire broadcasts a single event and (for match.* kinds) updates show_state
// so subsequent chat messages can reference the current match/round.
func (r *Runner) fire(ctx context.Context, showID string, idx int, ev Event) {
	log.Printf("showrunner[%s]: fire #%d %s", showID, idx, ev.Kind)

	switch ev.Kind {
	case KindMatchStart:
		var p struct {
			MatchID string `json:"match_id"`
		}
		if err := json.Unmarshal(ev.Payload, &p); err == nil {
			_ = r.store.SetState(ctx, chat.ShowState{
				ShowID:         showID,
				CurrentMatchID: p.MatchID,
				CurrentRound:   0,
			})
		}
	case KindMatchRound:
		var p struct {
			MatchID string `json:"match_id"`
			Round   int    `json:"round"`
		}
		if err := json.Unmarshal(ev.Payload, &p); err == nil {
			_ = r.store.SetState(ctx, chat.ShowState{
				ShowID:         showID,
				CurrentMatchID: p.MatchID,
				CurrentRound:   p.Round,
			})
		}
	case KindMatchEnd:
		// Clear active-match state so subsequent chat is not tagged.
		_ = r.store.SetState(ctx, chat.ShowState{ShowID: showID})
	}

	// Pass payload through unmodified — hub's marshaler handles json.RawMessage.
	r.hub.Broadcast(showID, string(ev.Kind), ev.Payload)
}

// LoadRunsheet parses a runsheet.json from disk, sorting events by time.
func LoadRunsheet(path string) (Runsheet, error) {
	var rs Runsheet
	body, err := os.ReadFile(path)
	if err != nil {
		return rs, err
	}
	if err := json.Unmarshal(body, &rs); err != nil {
		return rs, err
	}
	sort.SliceStable(rs.Events, func(i, j int) bool {
		return rs.Events[i].At.Before(rs.Events[j].At)
	})
	return rs, nil
}
