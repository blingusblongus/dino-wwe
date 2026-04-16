# Match schema

A pre-rendered match: outcome from the sim, narration approved by you.
Stored alongside the runsheet so the showrunner can pull narration into
`match.round` events as it ticks.

Path on disk: `data/shows/<show_id>/match_<n>.json`

## File shape

```json
{
  "match_id": "ep2-m1",
  "title": "#1 Contender's Match",
  "dinos": [
    { "slug": "anky", "name": "Anky Bronson", "starting_hp": 100.0 },
    { "slug": "velo", "name": "Velo Machado", "starting_hp": 100.0 }
  ],
  "rounds": [
    {
      "round": 1,
      "narration": "Anky lands the opening strike — 5.1 damage, Velo backs up but doesn't go down.",
      "hp": { "anky": 100.0, "velo": 94.9 },
      "events": [
        { "kind": "strike",  "by": "anky", "to": "velo", "damage": 5.1 },
        { "kind": "miss",    "by": "velo", "to": "anky" }
      ]
    },
    {
      "round": 7,
      "narration": "Anky lands the final shot of regulation. Velo is still up — he won't go down — but the scorecards are decided.",
      "hp": { "anky": 94.8, "velo": 79.5 },
      "events": [...]
    }
  ],
  "result": {
    "winner": "anky",
    "loser":  "velo",
    "method": "decision",
    "final_hp": { "anky": 94.8, "velo": 79.5 }
  },
  "stat_deltas": {
    "anky": { "confidence": 1, "motivation": 0 },
    "velo": { "confidence": -1, "motivation": 1 }
  }
}
```

## Notes

- `events` per round is the structured trace from the sim. The `narration`
  is the human-edited prose. The frontend only renders `narration`; the
  `events` payload is for analysts / debugging / future commentary
  generation.
- `stat_deltas` is the recipe to apply post-match. The next-pass runner
  reads these to compute the next episode's starting state.
- Round numbers don't have to be contiguous if a match ends by KO before
  round 7 — they reflect what actually happened.
