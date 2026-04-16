// Package api owns HTTP routes (REST + WebSocket upgrade) and the
// identity middleware that produces a stable user identity from either
// Authentik headers or an anonymous cookie.
package api

import (
	"embed"
	"io/fs"
	"log"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"

	"github.com/nallen/dino-wwe/server/internal/chat"
	"github.com/nallen/dino-wwe/server/internal/ws"
)

//go:embed all:static
var staticFS embed.FS

// indexHTML is read once at init so we can serve "/" with c.Data() and avoid
// http.FileServer's auto-redirect from /index.html → /, which loops forever
// when the / handler resolves back to index.html.
var indexHTML []byte

func init() {
	b, err := fs.ReadFile(staticFS, "static/index.html")
	if err != nil {
		log.Fatalf("api: read embedded static/index.html: %v", err)
	}
	indexHTML = b
}

type Deps struct {
	Hub              *ws.Hub
	Store            *chat.Store
	AnonCookieName   string
	TrustAuthHeaders bool
}

func NewRouter(deps Deps) http.Handler {
	r := gin.New()
	r.Use(gin.Recovery())
	r.Use(requestLogger())
	r.Use(identityMiddleware(deps))

	// Static test page (until Astro lands). Served as raw bytes to bypass
	// http.FileServer's index.html redirect behavior.
	r.GET("/", func(c *gin.Context) {
		c.Data(http.StatusOK, "text/html; charset=utf-8", indexHTML)
	})

	r.GET("/healthz", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})

	r.GET("/api/me", func(c *gin.Context) {
		ident := identityFromContext(c)
		c.JSON(http.StatusOK, gin.H{
			"user_id":   ident.UserID,
			"handle":    ident.Handle,
			"is_authed": ident.IsAuthed,
		})
	})

	// WebSocket upgrade endpoint. ShowID is whatever the caller wants —
	// rooms are created lazily on first connection.
	r.GET("/ws/shows/:show_id", func(c *gin.Context) {
		showID := c.Param("show_id")
		ident := identityFromContext(c)
		if err := ws.Serve(deps.Hub, showID, ws.Identity(ident), c.Writer, c.Request); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		}
	})

	return r
}

// ----- Middleware: identity -----

const identityKey = "identity"

type identity struct {
	UserID   string
	Handle   string
	IsAuthed bool
}

func identityMiddleware(deps Deps) gin.HandlerFunc {
	return func(c *gin.Context) {
		// 1. Trust Authentik headers if configured.
		if deps.TrustAuthHeaders {
			if uid := c.GetHeader("X-Authentik-Uid"); uid != "" {
				name := c.GetHeader("X-Authentik-Username")
				if name == "" {
					name = uid
				}
				c.Set(identityKey, identity{UserID: "auth:" + uid, Handle: name, IsAuthed: true})
				c.Next()
				return
			}
		}

		// 2. Fall back to anon cookie. Generate one if missing.
		cookie, err := c.Cookie(deps.AnonCookieName)
		if err != nil || cookie == "" {
			cookie = uuid.NewString()
			// 30-day cookie, lax samesite, httpOnly false so the front-end
			// can read it if it ever wants to (it doesn't need to today).
			c.SetCookie(deps.AnonCookieName, cookie, 60*60*24*30, "/", "", false, false)
		}
		c.Set(identityKey, identity{
			UserID:   "anon:" + cookie,
			Handle:   chat.HandleFor(cookie),
			IsAuthed: false,
		})
		c.Next()
	}
}

func identityFromContext(c *gin.Context) identity {
	v, ok := c.Get(identityKey)
	if !ok {
		return identity{Handle: "anon", UserID: "anon:unknown"}
	}
	return v.(identity)
}

// ----- Middleware: tiny request logger that won't spam during pings -----

func requestLogger() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Next()
		// Skip logging for the health endpoint to keep the stream readable.
		if c.Request.URL.Path == "/healthz" {
			return
		}
		gin.DefaultWriter.Write([]byte(
			c.Request.Method + " " + c.Request.URL.Path + "\n",
		))
	}
}
