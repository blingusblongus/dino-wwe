# Runsheet schema

A runsheet is the canonical wall-clock plan for a single show. The
showrunner walks one runsheet per show, firing each event at its `at`
timestamp.

Path on disk: `data/shows/<show_id>/runsheet.json`

## File shape

```json
{
  "show_id": "2026-04-17",
  "title": "WDAA Episode 2 — Evidence",
  "starts_at": "2026-04-17T20:00:00-04:00",
  "events": [
    {
      "at": "2026-04-17T20:00:00-04:00",
      "kind": "vignette.drop",
      "payload": {
        "ref": "blog/2026-04-18-ep2-recap-420-days-gone-in-seven-rounds",
        "title": "Cold Open"
      }
    },
    {
      "at": "2026-04-17T20:06:00-04:00",
      "kind": "match.start",
      "payload": {
        "match_id": "ep2-m1",
        "title": "#1 Contender's Match",
        "dinos": ["anky", "velo"]
      }
    },
    {
      "at": "2026-04-17T20:06:30-04:00",
      "kind": "match.round",
      "payload": {
        "match_id": "ep2-m1",
        "round": 1,
        "narration": "Anky walks Velo into the corner...",
        "hp": { "anky": 100.0, "velo": 94.9 }
      }
    },
    {
      "at": "2026-04-17T20:22:00-04:00",
      "kind": "match.end",
      "payload": {
        "match_id": "ep2-m1",
        "winner": "anky",
        "loser": "velo",
        "method": "decision"
      }
    }
  ]
}
```

## Event kinds

| Kind            | Payload                                                                          | Notes |
|-----------------|----------------------------------------------------------------------------------|-------|
| `vignette.drop` | `{ ref: string, title?: string }`                                                | Frontend fetches `ref` and renders. `ref` is an Astro content slug. |
| `match.start`   | `{ match_id, title?, dinos: [slug, slug] }`                                      | Updates `show_state.current_match_id`. Frontend opens match panel. |
| `match.round`   | `{ match_id, round, narration, hp: {dino_slug: float} }`                         | Updates `show_state.current_round`. Frontend appends round to log. |
| `match.end`     | `{ match_id, winner, loser, method: "decision" \| "ko" \| "interference" }`      | Clears current match. |

## Times

Always ISO 8601 with timezone offset. Server stores in UTC; frontend
renders in viewer locale. Don't use bare `2026-04-17T20:00:00`.

## Generation

The Python sim is the source of truth for runsheet contents. After
running an episode script, the next pass will add a `--write-runsheet`
flag that emits this JSON alongside the per-match files.
