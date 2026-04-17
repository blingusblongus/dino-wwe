"""LLM narration pass for matches and vignettes.

Uses Ollama by default (local, free). Swap to any OpenAI-compatible
endpoint by setting NARRATOR_BASE_URL and NARRATOR_MODEL env vars.

Falls back to mechanical narration if the LLM is unreachable.
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any

from sim import Dino, MatchData, RoundResult

# Config — override via env for different providers.
BASE_URL = os.environ.get("NARRATOR_BASE_URL", "http://localhost:11434")
MODEL = os.environ.get("NARRATOR_MODEL", "gemma4:latest")


def _chat(messages: list[dict[str, str]], temperature: float = 0.9) -> str:
    """Call the LLM chat endpoint. Returns the assistant message content."""
    body = json.dumps({
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            return data.get("message", {}).get("content", "").strip()
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print(f"  [narrator] LLM call failed: {e}")
        return ""


# ---- Context builders ----

@dataclass
class EpisodeContext:
    """Story context fed to the LLM for continuity and voice."""
    title: str
    storyline_threads: str   # free-text summary of active threads
    previous_outcomes: str   # what happened last episode
    roster_bios: str         # character bios for all relevant dinos


def _dino_bio(d: Dino) -> str:
    return (
        f"{d.name} ({d.species}), \"{d.slug}\" — "
        f"POW {d.power} DUR {d.durability} DEF {d.defense} "
        f"BRA {d.brains} XF {d.xfactor} | CONF {d.confidence} MOT {d.motivation}"
    )


def build_match_system(a: Dino, b: Dino, match_title: str, ctx: EpisodeContext) -> str:
    return f"""You are the lead commentator for the WDAA (World Dinosaur Athletic Association).
Your broadcast style: Attitude Era WWE. Think Jim Ross meets Jerry Lawler — genuine excitement,
dramatic gravitas, occasional humor, NEVER breaking kayfabe. These are real dinosaur athletes.

Show: {ctx.title}
Match: {match_title}

Competitors:
- {_dino_bio(a)}
- {_dino_bio(b)}

Active storylines:
{ctx.storyline_threads}

Previous episode:
{ctx.previous_outcomes}

RULES:
- Write 3-5 sentences per round of vivid play-by-play commentary.
- Reference signature moves, character traits, and ongoing feuds.
- Build tension across rounds — early rounds should simmer, later rounds should boil.
- Include crowd reactions, body language, and small character moments.
- If a counter happens, make it dramatic. If damage is low, describe it as a chess match.
- Use the competitors' names and epithets, not just "he/she."
- Do NOT use hashtags, emojis, or meta-commentary about wrestling being scripted.
- Do NOT start with "Round X" — the round number is shown separately.
- Keep it under 100 words per round."""


def build_vignette_system(ctx: EpisodeContext) -> str:
    return f"""You are a writer for the WDAA (World Dinosaur Athletic Association) TV show.
Your style: Attitude Era WWE television. Think backstage segments, parking lot confrontations,
and character-driven drama. These are real dinosaur athletes with real grievances.

Show: {ctx.title}

Active storylines:
{ctx.storyline_threads}

Previous episode:
{ctx.previous_outcomes}

Character reference:
{ctx.roster_bios}

RULES:
- Write 2-3 short paragraphs of vivid scene description with dialogue.
- Include stage direction (camera angles, lighting, body language).
- Dialogue should sound like real people talking, not narration. Keep it punchy.
- Build character — each dino has a voice. Rex is entitled, Anky is quiet, Velo is cocky, Dilo is theatrical.
- End each vignette on a beat that hooks the viewer (a look, a line, a reveal).
- Do NOT use hashtags, emojis, or break the fourth wall.
- Keep it under 250 words."""


# ---- Narration functions ----

def narrate_match(
    data: MatchData,
    match_title: str,
    ctx: EpisodeContext,
) -> list[str]:
    """Generate commentary for each round. Returns a list of narration strings,
    one per round. Falls back to mechanical narration on LLM failure."""
    a, b = data.dinos
    system = build_match_system(a, b, match_title, ctx)
    narrations: list[str] = []
    history = ""

    for rd in data.rounds:
        # Describe the mechanical events for the LLM to dramatize.
        mechanical = _describe_exchanges(rd, a, b)
        prompt = (
            f"{'Previous rounds commentary:' + chr(10) + history + chr(10) + chr(10) if history else ''}"
            f"Round {rd.round} mechanical events:\n{mechanical}\n\n"
            f"HP after round: {a.slug}={rd.hp.get(a.slug, '?')}, {b.slug}={rd.hp.get(b.slug, '?')}\n\n"
            f"Write the commentary for round {rd.round}."
        )

        result = _chat([
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ])

        if result:
            narrations.append(result)
            history += f"Round {rd.round}: {result}\n"
            print(f"  [narrator] round {rd.round} ✓ ({len(result)} chars)")
        else:
            # Fallback to mechanical narration.
            narrations.append(rd.narration)
            history += f"Round {rd.round}: {rd.narration}\n"
            print(f"  [narrator] round {rd.round} — fallback to mechanical")

    return narrations


def expand_vignette(
    title: str,
    beat: str,
    ctx: EpisodeContext,
) -> str:
    """Expand a short vignette beat into a full dramatic scene.
    Falls back to the original beat on LLM failure."""
    system = build_vignette_system(ctx)
    prompt = (
        f"Vignette: \"{title}\"\n\n"
        f"Beat to expand:\n{beat}\n\n"
        f"Write this scene."
    )

    result = _chat([
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ])

    if result:
        print(f"  [narrator] vignette \"{title}\" ✓ ({len(result)} chars)")
        return result
    else:
        print(f"  [narrator] vignette \"{title}\" — fallback to beat")
        return beat


# ---- Helpers ----

def _describe_exchanges(rd: RoundResult, a: Dino, b: Dino) -> str:
    """Convert structured exchanges to a mechanical description the LLM can dramatize."""
    lines = []
    for ex in rd.exchanges:
        if ex.kind == "strike":
            lines.append(f"{ex.by} strikes {ex.to} for {ex.damage} damage.")
        elif ex.kind == "counter":
            lines.append(f"{ex.to} attempted to strike {ex.by}, but {ex.by} read it and countered for {ex.damage} damage.")
        elif ex.kind == "interference":
            lines.append(f"INTERFERENCE: {ex.note or 'outside attack'} — {ex.to} takes {ex.damage} damage.")
    if not lines:
        lines.append("Both competitors circle, testing range. No significant contact.")
    return "\n".join(lines)
