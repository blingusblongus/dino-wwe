// Package ws holds the WebSocket hub, per-connection clients, and the
// JSON message contract spoken between server and browser.
package ws

import (
	"encoding/json"

	"github.com/nallen/dino-wwe/server/internal/chat"
)

// ----- Message kinds (server → client) -----
const (
	MsgHello         = "hello"
	MsgChatMessage   = "chat.message"
	MsgMatchStart    = "match.start"
	MsgMatchRound    = "match.round"
	MsgMatchEnd      = "match.end"
	MsgVignetteDrop  = "vignette.drop"
	MsgReactionBurst = "reaction.burst"
	MsgError         = "error"
)

// ----- Message kinds (client → server) -----
const (
	CMsgChatSend = "chat.send"
	CMsgReact    = "react"
)

// Envelope wraps everything on the wire so we can switch on Type.
type Envelope struct {
	Type    string          `json:"type"`
	Payload json.RawMessage `json:"payload,omitempty"`
}

// Hello is sent immediately after a successful connection. Carries the
// connection's identity (so the browser doesn't have to compute its own
// handle) and a backfill of recent chat messages so late joiners feel
// continuity.
// HelloEvent is a show event replayed in the hello backfill.
type HelloEvent struct {
	Kind    string          `json:"kind"`
	Payload json.RawMessage `json:"payload"`
}

type Hello struct {
	ShowID   string         `json:"show_id"`
	UserID   string         `json:"user_id"`
	Handle   string         `json:"handle"`
	IsAuthed bool           `json:"is_authed"`
	Backfill []chat.Message `json:"backfill"`
	Events   []HelloEvent   `json:"events"` // show events that already fired
}

// MatchStart announces an upcoming match. Dinos is a slice of two slugs
// matching the sim's roster keys (e.g. ["rex", "anky"]).
type MatchStart struct {
	MatchID string   `json:"match_id"`
	Title   string   `json:"title,omitempty"`
	Dinos   []string `json:"dinos"`
}

// MatchRound is one round's narration plus the post-round HP snapshot.
// The narration may be multiple lines.
type MatchRound struct {
	MatchID   string             `json:"match_id"`
	Round     int                `json:"round"`
	Narration string             `json:"narration"`
	HP        map[string]float64 `json:"hp,omitempty"`
}

// MatchEnd announces the result. Method is "decision" | "ko" | "interference".
type MatchEnd struct {
	MatchID string `json:"match_id"`
	Winner  string `json:"winner"`
	Loser   string `json:"loser"`
	Method  string `json:"method"`
}

// VignetteDrop tells the client a new blog post / vignette is now live.
// Ref is a relative path or content slug the frontend can fetch.
type VignetteDrop struct {
	Ref   string `json:"ref"`
	Title string `json:"title,omitempty"`
}

// ReactionBurst is a periodic aggregate of crowd reactions.
type ReactionBurst struct {
	WindowMs int     `json:"window_ms"`
	Cheer    float64 `json:"cheer"`
	Boo      float64 `json:"boo"`
}

// ----- Client → server payloads -----

type ChatSend struct {
	Text string `json:"text"`
}

type React struct {
	Value string `json:"value"` // "cheer" | "boo"
}

// ----- helpers -----

func mustEncode(kind string, payload any) []byte {
	raw, err := json.Marshal(payload)
	if err != nil {
		// Should never happen for our well-typed payloads.
		panic("ws: encode payload: " + err.Error())
	}
	env, err := json.Marshal(Envelope{Type: kind, Payload: raw})
	if err != nil {
		panic("ws: encode envelope: " + err.Error())
	}
	return env
}
