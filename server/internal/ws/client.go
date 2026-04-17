package ws

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/gorilla/websocket"
)

const (
	writeWait      = 10 * time.Second
	pongWait       = 60 * time.Second
	pingPeriod     = (pongWait * 9) / 10
	maxFrameBytes  = 4 << 10 // 4 KiB cap on a single inbound frame
)

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin: func(r *http.Request) bool {
		// POC: permissive. Tighten when we've decided what hostnames the
		// server will be reachable on (probably read from an allowlist env var).
		return true
	},
}

// Client wraps a single WebSocket connection.
type Client struct {
	hub      *Hub
	room     *Room
	conn     *websocket.Conn
	send     chan []byte
	userID   string
	handle   string
	isAuthed bool

	// Sliding-window rate limiter state.
	rlEvents []time.Time
}

// Identity is what the API layer hands the WS layer when promoting an HTTP
// request to a WebSocket.
type Identity struct {
	UserID   string
	Handle   string
	IsAuthed bool
}

// Serve upgrades the request, registers a Client into the room, and runs
// read+write loops until either side disconnects.
func Serve(hub *Hub, showID string, ident Identity, w http.ResponseWriter, r *http.Request) error {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		return err
	}

	room := hub.Room(showID)
	c := &Client{
		hub:      hub,
		room:     room,
		conn:     conn,
		send:     make(chan []byte, 32),
		userID:   ident.UserID,
		handle:   ident.Handle,
		isAuthed: ident.IsAuthed,
	}

	// Send hello (with backfill) before announcing membership so the new
	// client always sees its own context first.
	backfill, err := hub.Store().Backfill(r.Context(), showID, 100)
	if err != nil {
		log.Printf("chat backfill: %v", err)
	}

	// Event backfill — replay all show events that already fired.
	storedEvents, err := hub.Store().EventBackfill(r.Context(), showID)
	if err != nil {
		log.Printf("event backfill: %v", err)
	}
	var helloEvents []HelloEvent
	for _, se := range storedEvents {
		helloEvents = append(helloEvents, HelloEvent{
			Kind:    se.Kind,
			Payload: json.RawMessage(se.Payload),
		})
	}

	hello := mustEncode(MsgHello, Hello{
		ShowID:   showID,
		UserID:   ident.UserID,
		Handle:   ident.Handle,
		IsAuthed: ident.IsAuthed,
		Backfill: backfill,
		Events:   helloEvents,
	})
	c.send <- hello

	room.register <- c

	go c.writePump()
	go c.readPump()
	return nil
}

func (c *Client) readPump() {
	defer func() {
		c.room.unregister <- c
		_ = c.conn.Close()
	}()

	c.conn.SetReadLimit(maxFrameBytes)
	_ = c.conn.SetReadDeadline(time.Now().Add(pongWait))
	c.conn.SetPongHandler(func(string) error {
		_ = c.conn.SetReadDeadline(time.Now().Add(pongWait))
		return nil
	})

	for {
		_, raw, err := c.conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("client[%s] read err: %v", c.handle, err)
			}
			return
		}
		c.handleInbound(raw)
	}
}

func (c *Client) handleInbound(raw []byte) {
	var env Envelope
	if err := json.Unmarshal(raw, &env); err != nil {
		c.sendError("malformed_envelope")
		return
	}
	switch env.Type {
	case CMsgChatSend:
		var p ChatSend
		if err := json.Unmarshal(env.Payload, &p); err != nil {
			c.sendError("malformed_payload")
			return
		}
		text := strings.TrimSpace(p.Text)
		if text == "" {
			return
		}
		if len(text) > c.hub.limits.MaxMessageLen {
			text = text[:c.hub.limits.MaxMessageLen]
		}
		if !c.allowRate() {
			c.sendError("rate_limited")
			return
		}
		ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		defer cancel()
		c.room.PersistAndBroadcastChat(ctx, c, text)

	case CMsgReact:
		// Aggregation for reactions will land in the next pass; for now,
		// accept-and-ignore so the frontend can wire the button up early.
		var p React
		_ = json.Unmarshal(env.Payload, &p)

	default:
		c.sendError("unknown_type")
	}
}

func (c *Client) allowRate() bool {
	now := time.Now()
	cutoff := now.Add(-c.hub.limits.RateLimitWindow)
	// Drop expired timestamps.
	kept := c.rlEvents[:0]
	for _, t := range c.rlEvents {
		if t.After(cutoff) {
			kept = append(kept, t)
		}
	}
	c.rlEvents = kept
	if len(c.rlEvents) >= c.hub.limits.RateLimitMsgs {
		return false
	}
	c.rlEvents = append(c.rlEvents, now)
	return true
}

func (c *Client) sendError(code string) {
	select {
	case c.send <- mustEncode(MsgError, map[string]string{"code": code}):
	default:
	}
}

func (c *Client) writePump() {
	ticker := time.NewTicker(pingPeriod)
	defer func() {
		ticker.Stop()
		_ = c.conn.Close()
	}()
	for {
		select {
		case msg, ok := <-c.send:
			_ = c.conn.SetWriteDeadline(time.Now().Add(writeWait))
			if !ok {
				_ = c.conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}
			if err := c.conn.WriteMessage(websocket.TextMessage, msg); err != nil {
				return
			}
		case <-ticker.C:
			_ = c.conn.SetWriteDeadline(time.Now().Add(writeWait))
			if err := c.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}
