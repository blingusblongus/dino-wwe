/**
 * WebSocket client for Dino-WWE shows.
 *
 * Manages connection lifecycle, dispatches typed events to handlers,
 * auto-reconnects with exponential backoff.
 */

export interface Envelope {
  type: string;
  payload: any;
}

export type EventHandler = (payload: any) => void;

export class WsClient {
  private ws: WebSocket | null = null;
  private handlers = new Map<string, EventHandler[]>();
  private showId: string;
  private retryMs = 1000;
  private maxRetry = 15000;
  private closed = false;

  constructor(showId: string) {
    this.showId = showId;
  }

  on(type: string, fn: EventHandler): this {
    const list = this.handlers.get(type) || [];
    list.push(fn);
    this.handlers.set(type, list);
    return this;
  }

  async connect(): Promise<void> {
    // Hit /api/me first to ensure the anon cookie exists before the WS
    // handshake — cookies set during upgrade don't always stick.
    try {
      await fetch("/api/me", { credentials: "include" });
    } catch {}

    this.doConnect();
  }

  send(type: string, payload: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, payload }));
    }
  }

  close(): void {
    this.closed = true;
    this.ws?.close();
  }

  private doConnect(): void {
    if (this.closed) return;

    const proto = location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${location.host}/ws/shows/${encodeURIComponent(this.showId)}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.retryMs = 1000;
      this.dispatch("_connected", null);
    };

    this.ws.onmessage = (ev) => {
      try {
        const env: Envelope = JSON.parse(ev.data);
        this.dispatch(env.type, env.payload);
      } catch {}
    };

    this.ws.onclose = () => {
      this.dispatch("_disconnected", null);
      if (!this.closed) {
        setTimeout(() => this.doConnect(), this.retryMs);
        this.retryMs = Math.min(this.retryMs * 1.5, this.maxRetry);
      }
    };

    this.ws.onerror = () => {}; // onclose handles reconnect
  }

  /** Replay a stored event through the handler pipeline (used for backfill). */
  replay(type: string, payload: any): void {
    this.dispatch(type, payload);
  }

  private dispatch(type: string, payload: any): void {
    const list = this.handlers.get(type);
    if (list) list.forEach((fn) => fn(payload));
  }
}
