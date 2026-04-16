// Dino-WWE server: HTTP + WebSocket + SQLite chat persistence.
//
// First-pass scope: chat rooms with anonymous handles, message persistence,
// backfill on connect. Match-event broadcasting is stubbed; auth middleware
// reads optional X-Authentik-* headers but does not enforce.
package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"

	"github.com/nallen/dino-wwe/server/internal/api"
	"github.com/nallen/dino-wwe/server/internal/chat"
	"github.com/nallen/dino-wwe/server/internal/showrunner"
	"github.com/nallen/dino-wwe/server/internal/ws"
)

func main() {
	cfg, err := LoadConfig()
	if err != nil {
		log.Fatalf("config: %v", err)
	}
	log.Printf("starting dino-wwe server | listen=%s data=%s content=%s",
		cfg.ListenAddr, cfg.DataDir, cfg.ContentDir)

	// Open SQLite + run migrations.
	store, err := chat.NewStore(cfg.ChatDBPath())
	if err != nil {
		log.Fatalf("chat store: %v", err)
	}
	defer store.Close()

	// Hub manages all show rooms + WebSocket connections.
	hub := ws.NewHub(store, ws.Limits{
		MaxMessageLen:    cfg.ChatMaxMessageLen,
		RateLimitMsgs:    cfg.ChatRateLimitMsgs,
		RateLimitWindow:  time.Duration(cfg.ChatRateLimitWindowMs) * time.Millisecond,
	})

	// Showrunner is a stub for now — loads runsheets but doesn't broadcast yet.
	runner := showrunner.New(cfg.DataDir, hub)
	go runner.Start(context.Background())

	// HTTP routes.
	if cfg.GinMode != "" {
		gin.SetMode(cfg.GinMode)
	}
	router := api.NewRouter(api.Deps{
		Hub:              hub,
		Store:            store,
		AnonCookieName:   cfg.AnonCookieName,
		TrustAuthHeaders: cfg.TrustAuthHeaders,
	})

	srv := &http.Server{
		Addr:              cfg.ListenAddr,
		Handler:           router,
		ReadHeaderTimeout: 5 * time.Second,
	}

	// Graceful shutdown on SIGINT/SIGTERM.
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	go func() {
		log.Printf("listening on %s", cfg.ListenAddr)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Fatalf("listen: %v", err)
		}
	}()

	<-ctx.Done()
	log.Println("shutdown signal received")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		log.Printf("shutdown: %v", err)
	}
	hub.Close()
	log.Println("bye")
}
