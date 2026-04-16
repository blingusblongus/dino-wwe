"""Runsheet + per-match JSON writer.

Walks an episode's "plan" (an ordered list of Vignette and Match items),
runs the sim for each match, and lays everything out on a wall-clock
timeline in a runsheet.json plus one match_<n>.json per match.

Schemas live in ../schemas/runsheet.md and ../schemas/match.md.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Union

from sim import Dino, MatchData, simulate


# ----- Show plan items -----

@dataclass
class Vignette:
    title: str
    text: str | None = None      # inline narration shown live
    ref: str | None = None       # OR an external content slug


@dataclass
class Match:
    match_id: str
    title: str
    a: Dino
    b: Dino
    seed: int | None = None
    interference: dict | None = None


PlanItem = Union[Vignette, Match]


# ----- Writer -----

@dataclass
class TimingConfig:
    vignette_seconds: int = 25      # how long a vignette "lasts" before next item
    match_intro_seconds: int = 8    # gap between match.start and round 1
    round_seconds: int = 10         # gap between consecutive rounds
    match_outro_seconds: int = 8    # gap between final round and match.end
    inter_match_seconds: int = 15   # gap after match.end before next item


@dataclass
class WrittenShow:
    show_id: str
    runsheet_path: Path
    match_paths: list[Path]
    starts_at: datetime
    ends_at: datetime
    n_events: int


def write_show(
    *,
    out_dir: str | os.PathLike,
    show_id: str,
    title: str,
    starts_at: datetime,
    plan: Iterable[PlanItem],
    timing: TimingConfig | None = None,
) -> WrittenShow:
    timing = timing or TimingConfig()
    show_dir = Path(out_dir) / "shows" / show_id
    show_dir.mkdir(parents=True, exist_ok=True)

    events: list[dict[str, Any]] = []
    match_paths: list[Path] = []
    cursor = starts_at
    match_idx = 0

    for item in plan:
        if isinstance(item, Vignette):
            payload: dict[str, Any] = {"title": item.title}
            if item.text is not None:
                payload["text"] = item.text
            if item.ref is not None:
                payload["ref"] = item.ref
            events.append({
                "at": _iso(cursor),
                "kind": "vignette.drop",
                "payload": payload,
            })
            cursor += timedelta(seconds=timing.vignette_seconds)

        elif isinstance(item, Match):
            match_idx += 1
            data = simulate(item.a, item.b, seed=item.seed, interference=item.interference)

            # Persist the per-match JSON.
            match_path = show_dir / f"match_{match_idx}.json"
            match_path.write_text(json.dumps(_serialize_match(item, data), indent=2))
            match_paths.append(match_path)

            # match.start
            events.append({
                "at": _iso(cursor),
                "kind": "match.start",
                "payload": {
                    "match_id": item.match_id,
                    "title": item.title,
                    "dinos": [item.a.slug, item.b.slug],
                },
            })
            cursor += timedelta(seconds=timing.match_intro_seconds)

            # one event per round
            for rd in data.rounds:
                events.append({
                    "at": _iso(cursor),
                    "kind": "match.round",
                    "payload": {
                        "match_id": item.match_id,
                        "round": rd.round,
                        "narration": rd.narration,
                        "hp": rd.hp,
                    },
                })
                cursor += timedelta(seconds=timing.round_seconds)

            # match.end (after a brief outro pause)
            cursor += timedelta(seconds=timing.match_outro_seconds - timing.round_seconds)
            if cursor < starts_at:
                cursor = starts_at  # paranoia
            events.append({
                "at": _iso(cursor),
                "kind": "match.end",
                "payload": {
                    "match_id": item.match_id,
                    "winner": data.winner.slug,
                    "loser": data.loser.slug,
                    "method": data.method,
                    "final_hp": data.final_hp,
                },
            })
            cursor += timedelta(seconds=timing.inter_match_seconds)

        else:
            raise TypeError(f"Unknown plan item type: {type(item).__name__}")

    runsheet = {
        "show_id": show_id,
        "title": title,
        "starts_at": _iso(starts_at),
        "events": events,
    }
    runsheet_path = show_dir / "runsheet.json"
    runsheet_path.write_text(json.dumps(runsheet, indent=2))

    return WrittenShow(
        show_id=show_id,
        runsheet_path=runsheet_path,
        match_paths=match_paths,
        starts_at=starts_at,
        ends_at=cursor,
        n_events=len(events),
    )


# ----- Internal helpers -----

def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _serialize_match(item: Match, data: MatchData) -> dict[str, Any]:
    return {
        "match_id": item.match_id,
        "title": item.title,
        "dinos": [
            {
                "slug": d.slug,
                "name": d.name,
                "species": d.species,
                "starting_hp": 100.0,
                "stats": {
                    "power": d.power,
                    "durability": d.durability,
                    "defense": d.defense,
                    "brains": d.brains,
                    "xfactor": d.xfactor,
                    "confidence": d.confidence,
                    "motivation": d.motivation,
                },
            }
            for d in data.dinos
        ],
        "rounds": [
            {
                "round": rd.round,
                "narration": rd.narration,
                "hp": rd.hp,
                "exchanges": [
                    {
                        "kind": ex.kind,
                        "by": ex.by,
                        "to": ex.to,
                        "damage": ex.damage,
                        **({"note": ex.note} if ex.note else {}),
                    }
                    for ex in rd.exchanges
                ],
            }
            for rd in data.rounds
        ],
        "result": {
            "winner": data.winner.slug,
            "loser": data.loser.slug,
            "method": data.method,
            "final_hp": data.final_hp,
        },
    }
