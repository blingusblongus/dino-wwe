package ws

import (
	"context"
	"log"
	"sync"
	"time"

	"github.com/nallen/dino-wwe/server/internal/chat"
)

// Limits is the configurable behaviour wrapper for the hub.
type Limits struct {
	MaxMessageLen   int
	RateLimitMsgs   int
	RateLimitWindow time.Duration
}

// Hub owns the room registry. There is one hub per server process.
type Hub struct {
	store  *chat.Store
	limits Limits

	mu    sync.Mutex
	rooms map[string]*Room

	closed chan struct{}
}

func NewHub(store *chat.Store, limits Limits) *Hub {
	return &Hub{
		store:  store,
		limits: limits,
		rooms:  make(map[string]*Room),
		closed: make(chan struct{}),
	}
}

// Room returns the existing room for showID or lazily creates one.
func (h *Hub) Room(showID string) *Room {
	h.mu.Lock()
	defer h.mu.Unlock()
	if r, ok := h.rooms[showID]; ok {
		return r
	}
	r := newRoom(showID, h)
	h.rooms[showID] = r
	go r.run()
	return r
}

// Broadcast sends a pre-encoded envelope to every connected client of a show.
// Used by the showrunner for match events / vignette drops.
func (h *Hub) Broadcast(showID string, kind string, payload any) {
	r := h.Room(showID)
	r.broadcast <- mustEncode(kind, payload)
}

func (h *Hub) Limits() Limits { return h.limits }
func (h *Hub) Store() *chat.Store { return h.store }

func (h *Hub) Close() {
	h.mu.Lock()
	defer h.mu.Unlock()
	select {
	case <-h.closed:
		return
	default:
	}
	close(h.closed)
	for _, r := range h.rooms {
		close(r.shutdown)
	}
}

// Room is one show's chat room: its own broadcast loop + connected clients.
type Room struct {
	hub    *Hub
	showID string

	register   chan *Client
	unregister chan *Client
	broadcast  chan []byte
	shutdown   chan struct{}

	clients map[*Client]struct{}
}

func newRoom(showID string, hub *Hub) *Room {
	return &Room{
		hub:        hub,
		showID:     showID,
		register:   make(chan *Client, 8),
		unregister: make(chan *Client, 8),
		broadcast:  make(chan []byte, 64),
		shutdown:   make(chan struct{}),
		clients:    make(map[*Client]struct{}),
	}
}

// run is the room's single-writer loop — owns all client membership state.
func (r *Room) run() {
	log.Printf("room[%s] started", r.showID)
	defer log.Printf("room[%s] stopped", r.showID)

	for {
		select {
		case c := <-r.register:
			r.clients[c] = struct{}{}
			log.Printf("room[%s] +client (%d total) handle=%s", r.showID, len(r.clients), c.handle)

		case c := <-r.unregister:
			if _, ok := r.clients[c]; ok {
				delete(r.clients, c)
				close(c.send)
				log.Printf("room[%s] -client (%d total) handle=%s", r.showID, len(r.clients), c.handle)
			}

		case msg := <-r.broadcast:
			for c := range r.clients {
				select {
				case c.send <- msg:
				default:
					// Slow client — drop them rather than block the room.
					delete(r.clients, c)
					close(c.send)
					log.Printf("room[%s] dropped slow client handle=%s", r.showID, c.handle)
				}
			}

		case <-r.shutdown:
			for c := range r.clients {
				close(c.send)
			}
			return
		}
	}
}

// PersistAndBroadcastChat: called from a client read loop when a chat.send
// arrives. Stores to SQLite, then fans out to the room.
func (r *Room) PersistAndBroadcastChat(ctx context.Context, sender *Client, text string) {
	state, err := r.hub.store.CurrentState(ctx, r.showID)
	if err != nil {
		log.Printf("room[%s] state lookup: %v", r.showID, err)
	}
	msg := chat.Message{
		ShowID:   r.showID,
		MatchID:  state.CurrentMatchID,
		Round:    state.CurrentRound,
		UserID:   sender.userID,
		Handle:   sender.handle,
		IsAuthed: sender.isAuthed,
		Text:     text,
		AtMs:     time.Now().UnixMilli(),
	}
	saved, err := r.hub.store.Save(ctx, msg)
	if err != nil {
		log.Printf("room[%s] save chat: %v", r.showID, err)
		return
	}
	r.broadcast <- mustEncode(MsgChatMessage, saved)
}
