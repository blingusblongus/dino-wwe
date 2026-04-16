package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strconv"
)

type Config struct {
	ListenAddr            string
	DataDir               string
	ContentDir            string
	ChatRateLimitMsgs     int
	ChatRateLimitWindowMs int
	ChatMaxMessageLen     int
	AnonCookieName        string
	TrustAuthHeaders      bool
	GinMode               string
}

func (c Config) ChatDBPath() string {
	return filepath.Join(c.DataDir, "chat.db")
}

func LoadConfig() (Config, error) {
	c := Config{
		ListenAddr:            envStr("LISTEN_ADDR", ":9090"),
		DataDir:               envStr("DATA_DIR", "./data"),
		ContentDir:            envStr("CONTENT_DIR", "./content"),
		ChatRateLimitMsgs:     envInt("CHAT_RATE_LIMIT_MSGS", 20),
		ChatRateLimitWindowMs: envInt("CHAT_RATE_LIMIT_WINDOW_MS", 10000),
		ChatMaxMessageLen:     envInt("CHAT_MAX_MESSAGE_LEN", 500),
		AnonCookieName:        envStr("ANON_COOKIE_NAME", "dwwa_anon"),
		TrustAuthHeaders:      envBool("TRUST_AUTH_HEADERS", false),
		GinMode:               envStr("GIN_MODE", ""),
	}
	if err := os.MkdirAll(c.DataDir, 0o755); err != nil {
		return c, fmt.Errorf("create data dir: %w", err)
	}
	return c, nil
}

func envStr(key, def string) string {
	if v, ok := os.LookupEnv(key); ok {
		return v
	}
	return def
}

func envInt(key string, def int) int {
	if v, ok := os.LookupEnv(key); ok {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return def
}

func envBool(key string, def bool) bool {
	if v, ok := os.LookupEnv(key); ok {
		if b, err := strconv.ParseBool(v); err == nil {
			return b
		}
	}
	return def
}
