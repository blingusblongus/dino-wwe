# --- Build stage ---
FROM golang:1.26-alpine AS build

WORKDIR /src
COPY go.mod go.sum* ./
RUN go mod download || true

COPY . .
# CGO disabled so we get a static binary; modernc.org/sqlite is pure Go.
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /out/server .

# --- Runtime stage ---
FROM gcr.io/distroless/static-debian12:nonroot

WORKDIR /app
COPY --from=build /out/server /app/server

# Migrations + static assets are embedded into the binary via go:embed,
# so we don't need to copy them here.

ENV LISTEN_ADDR=":9090"
EXPOSE 9090
USER nonroot:nonroot
ENTRYPOINT ["/app/server"]
