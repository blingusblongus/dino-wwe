// Package showrunner walks a show's runsheet and broadcasts the events at
// their scheduled times.
//
// First-pass scope: the runsheet schema is locked in below, the loader
// works, but the broadcast loop is intentionally a no-op. The next pass
// will plumb runsheet events through to hub.Broadcast.
package showrunner

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sort"
	"time"
)

// EventKind identifies what action the showrunner should take at an event's
// scheduled time.
type EventKind string

const (
	KindMatchStart   EventKind = "match.start"
	KindMatchRound   EventKind = "match.round"
	KindMatchEnd     EventKind = "match.end"
	KindVignetteDrop EventKind = "vignette.drop"
)

// Event is one entry in a runsheet.
type Event struct {
	At      time.Time       `json:"at"`              // when to fire
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
// as an interface here keeps the import graph clean and lets us mock it.
type Hub interface {
	Broadcast(showID, kind string, payload any)
}

// Runner discovers runsheets under <data>/shows/*/runsheet.json and walks
// each one in its own goroutine.
type Runner struct {
	dataDir string
	hub     Hub
}

func New(dataDir string, hub Hub) *Runner {
	return &Runner{dataDir: dataDir, hub: hub}
}

// Start scans for runsheets and launches a goroutine per show whose end has
// not yet passed. Currently a stub: it logs what it would do, but does not
// broadcast events. Wiring to the hub lands in the next pass.
func (r *Runner) Start(ctx context.Context) {
	dir := filepath.Join(r.dataDir, "shows")
	entries, err := os.ReadDir(dir)
	if err != nil {
		if os.IsNotExist(err) {
			log.Printf("showrunner: %s does not exist yet — nothing to load", dir)
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
		log.Printf("showrunner: loaded show=%s title=%q events=%d (broadcast disabled in this pass)",
			rs.ShowID, rs.Title, len(rs.Events))
		// Next pass: spawn r.walk(ctx, rs)
	}
}

// LoadRunsheet parses a runsheet.json from disk, sorting events by time.
func LoadRunsheet(path string) (Runsheet, error) {
	var rs Runsheet
	body, err := os.ReadFile(path)
	if err != nil {
		return rs, fmt.Errorf("read: %w", err)
	}
	if err := json.Unmarshal(body, &rs); err != nil {
		return rs, fmt.Errorf("unmarshal: %w", err)
	}
	sort.SliceStable(rs.Events, func(i, j int) bool {
		return rs.Events[i].At.Before(rs.Events[j].At)
	})
	return rs, nil
}
