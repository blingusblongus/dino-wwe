.PHONY: up down logs build server-dev tidy fresh-db sim-ep1 sim-ep2 help

help:
	@echo "Targets:"
	@echo "  up           - docker compose up -d (server only)"
	@echo "  down         - docker compose down"
	@echo "  logs         - tail server logs"
	@echo "  build        - rebuild server image"
	@echo "  server-dev   - run server locally (no docker), bind to :9090"
	@echo "                 (host port for compose set via HOST_PORT, default 19090)"
	@echo "  tidy         - go mod tidy in ./server"
	@echo "  fresh-db     - delete chat.db and restart server"
	@echo "  sim-ep1      - run Episode 1 sim in container (prints to stdout)"
	@echo "  sim-ep2      - run Episode 2 sim in container (prints to stdout)"

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f server

build:
	docker compose build server

server-dev:
	cd server && go build -o ./bin/server . && \
	    DATA_DIR=$(CURDIR)/data CONTENT_DIR=$(CURDIR)/content exec ./bin/server

tidy:
	cd server && go mod tidy

fresh-db:
	rm -f data/chat.db data/chat.db-shm data/chat.db-wal
	-docker compose restart server

sim-ep1:
	docker compose run --rm sim python episode_1.py

sim-ep2:
	docker compose run --rm sim python episode_2.py
