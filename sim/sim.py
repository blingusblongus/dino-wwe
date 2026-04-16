"""WDAA match simulator (POC v0.2).

Hybrid model: the sim decides outcomes probabilistically from stats + mental
state. Narrative is authored separately. Stats range 1-10. Mental stats
(confidence, motivation) fluctuate episode-to-episode based on vignettes and
match results.

simulate() returns a MatchData object containing:
  - structured per-round events (for JSON export to runsheets)
  - the human-readable text log (for stdout / quick inspection)
  - winner/loser/method (the outcome)

Backward compatibility: callers who want the old (winner, loser, log) tuple
can read .winner / .loser / .log off MatchData.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class Dino:
    slug: str               # short id used in JSON payloads (e.g. "rex")
    name: str               # display name (e.g. "Rex Kingston")
    species: str
    # Physical (relatively stable across a season):
    power: int
    durability: int
    defense: int
    brains: int
    xfactor: int
    # Mental (fluctuates — modified by vignettes and results):
    confidence: int
    motivation: int
    # Per-match:
    hp: float = 100.0

    def offense_roll(self) -> float:
        base = self.power + random.uniform(0, self.xfactor)
        conf_mod = (self.confidence / 10.0) * 0.6 + 0.4      # 0.4x..1.0x
        mot_mod = (self.motivation / 10.0) * 0.4 + 0.6        # 0.6x..1.0x
        return base * conf_mod * mot_mod

    def defense_roll(self) -> float:
        base = (self.durability + self.defense) / 2.0
        mot_mod = (self.motivation / 10.0) * 0.3 + 0.7        # 0.7x..1.0x
        return base * mot_mod

    def counters(self) -> bool:
        # Brains drive counter probability. Brains 10 ~= 36% per defensive action.
        return random.random() < (self.brains / 28.0)


# ----- Structured per-round event records (for JSON export) -----

@dataclass
class Exchange:
    kind: str       # "strike" | "counter" | "interference"
    by: str         # slug of the actor
    to: str         # slug of the target
    damage: float   # rounded to 1dp downstream
    note: str = ""  # free-form annotation, e.g. interference details


@dataclass
class RoundResult:
    round: int
    exchanges: list[Exchange]
    hp: dict[str, float]    # post-round HP, by slug
    narration: str          # the round's text log lines joined


@dataclass
class MatchData:
    dinos: tuple[Dino, Dino]
    rounds: list[RoundResult]
    winner: Dino
    loser: Dino
    method: str             # "ko" | "decision" | "interference"
    log: list[str] = field(default_factory=list)

    @property
    def final_hp(self) -> dict[str, float]:
        return {d.slug: round(d.hp, 1) for d in self.dinos}


# ----- Internals -----

def _exchange(
    attacker: Dino,
    defender: Dino,
    log: list[str],
    round_log: list[str],
    exchanges: list[Exchange],
) -> None:
    if defender.counters():
        off = defender.offense_roll() * 0.65
        dmg = max(0.0, off - attacker.defense / 3.0) * 1.2
        attacker.hp -= dmg
        line = (
            f"    {defender.name} reads it and reverses for {dmg:.1f}."
            f"  [{attacker.name} HP {attacker.hp:.1f}]"
        )
        log.append(line)
        round_log.append(line)
        exchanges.append(Exchange(kind="counter", by=defender.slug, to=attacker.slug, damage=round(dmg, 1)))
    else:
        off = attacker.offense_roll()
        dfn = defender.defense_roll()
        dmg = max(0.0, off - dfn) * 1.25
        defender.hp -= dmg
        line = (
            f"    {attacker.name} lands for {dmg:.1f}."
            f"  [{defender.name} HP {defender.hp:.1f}]"
        )
        log.append(line)
        round_log.append(line)
        exchanges.append(Exchange(kind="strike", by=attacker.slug, to=defender.slug, damage=round(dmg, 1)))


def simulate(
    a: Dino,
    b: Dino,
    *,
    max_rounds: int = 7,
    seed: int | None = None,
    interference: dict | None = None,
) -> MatchData:
    """Simulate a match and return MatchData (structured rounds + text log).

    interference: optional dict describing a scripted run-in check.
      {round: int, chance: float, actor: str, target: Dino, damage: float}
    """
    if seed is not None:
        random.seed(seed)
    a.hp = b.hp = 100.0

    log = [f"=== {a.name} vs. {b.name} ==="]
    rounds: list[RoundResult] = []
    method = "decision"
    early_exit = False
    winner: Dino | None = None
    loser: Dino | None = None

    for r in range(1, max_rounds + 1):
        log.append(f"[Round {r}]")
        round_log: list[str] = [f"[Round {r}]"]
        exchanges: list[Exchange] = []

        first, second = (a, b) if random.random() < 0.5 else (b, a)
        _exchange(first, second, log, round_log, exchanges)
        if second.hp <= 0:
            line = f">>> KO: {first.name} wins in round {r}. <<<"
            log.append(line); round_log.append(line)
            rounds.append(RoundResult(round=r, exchanges=exchanges,
                                       hp={a.slug: round(a.hp, 1), b.slug: round(b.hp, 1)},
                                       narration="\n".join(round_log)))
            winner, loser, method, early_exit = first, second, "ko", True
            break

        _exchange(second, first, log, round_log, exchanges)
        if first.hp <= 0:
            line = f">>> KO: {second.name} wins in round {r}. <<<"
            log.append(line); round_log.append(line)
            rounds.append(RoundResult(round=r, exchanges=exchanges,
                                       hp={a.slug: round(a.hp, 1), b.slug: round(b.hp, 1)},
                                       narration="\n".join(round_log)))
            winner, loser, method, early_exit = second, first, "ko", True
            break

        if interference and r == interference["round"]:
            actor = interference["actor"]
            target: Dino = interference["target"]
            dmg = float(interference["damage"])
            if random.random() < interference["chance"]:
                target.hp -= dmg
                line = (
                    f"    >>> INTERFERENCE: {actor} strikes "
                    f"{target.name} for {dmg:.1f}. <<<"
                    f"  [HP {target.hp:.1f}]"
                )
                log.append(line); round_log.append(line)
                exchanges.append(Exchange(kind="interference", by="run-in", to=target.slug,
                                          damage=round(dmg, 1),
                                          note=f"{actor} interferes"))
                if target.hp <= 0:
                    other = a if target is b else b
                    line = f">>> {other.name} wins in round {r} after outside interference. <<<"
                    log.append(line); round_log.append(line)
                    rounds.append(RoundResult(round=r, exchanges=exchanges,
                                               hp={a.slug: round(a.hp, 1), b.slug: round(b.hp, 1)},
                                               narration="\n".join(round_log)))
                    winner, loser, method, early_exit = other, target, "interference", True
                    break
            else:
                line = (
                    f"    (Interference threatened by {actor} "
                    f"but never materialized.)"
                )
                log.append(line); round_log.append(line)

        rounds.append(RoundResult(round=r, exchanges=exchanges,
                                   hp={a.slug: round(a.hp, 1), b.slug: round(b.hp, 1)},
                                   narration="\n".join(round_log)))

    if not early_exit:
        winner, loser = (a, b) if a.hp > b.hp else (b, a)
        log.append(
            f">>> DECISION: {winner.name} ({winner.hp:.1f}) defeats "
            f"{loser.name} ({loser.hp:.1f}). <<<"
        )

    assert winner is not None and loser is not None  # for type-checker
    return MatchData(
        dinos=(a, b),
        rounds=rounds,
        winner=winner,
        loser=loser,
        method=method,
        log=log,
    )
