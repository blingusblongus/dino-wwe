"""WDAA match simulator (POC v0.3).

Hybrid model: the sim decides outcomes probabilistically from stats + mental
state. Narrative is authored separately. Stats range 1-10. Mental stats
(confidence, motivation) fluctuate episode-to-episode based on vignettes and
match results.

Match endings:
  - KO: HP drops to 0 from a strike/counter (always checked).
  - Finish check: after each exchange, there's a probability of a finish
    that scales with accumulated damage and round number. Finish type
    depends on the attacker's stats:
      * power >= brains → KO
      * brains > power  → submission
      * otherwise       → TKO (ref stoppage)
  - Decision: if nobody is finished after max_rounds.

This means matches vary in length (some end round 2, some go the distance)
and ending type, producing more dynamic storytelling material.
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
        return random.random() < (self.brains / 28.0)


# ----- Structured per-round event records (for JSON export) -----

@dataclass
class Exchange:
    kind: str       # "strike" | "counter" | "interference" | "finish"
    by: str         # slug of the actor
    to: str         # slug of the target
    damage: float   # rounded to 1dp downstream
    note: str = ""  # free-form annotation


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
    method: str             # "ko" | "tko" | "submission" | "decision" | "interference"
    finish_round: int | None = None  # round the match ended, or None for decision
    log: list[str] = field(default_factory=list)

    @property
    def final_hp(self) -> dict[str, float]:
        return {d.slug: round(d.hp, 1) for d in self.dinos}


# ----- Finish check -----

def _finish_method(attacker: Dino) -> str:
    """Pick a finish type based on the attacker's stat profile."""
    if attacker.brains > attacker.power:
        return "submission"
    elif attacker.power >= 8:
        return "ko"
    else:
        return "tko"


def _check_finish(
    attacker: Dino,
    defender: Dino,
    round_num: int,
    max_rounds: int,
    damage_dealt: float,
) -> str | None:
    """Roll for a finish. Returns a method string if the match should end,
    None if it continues.

    Probability formula:
      base       = 0.08  (8% base per check — there are 2 checks/round)
      damage_mod = (100 - defender.hp) / 100  (more hurt = more vulnerable)
      round_mod  = round / max_rounds  (later rounds = more likely finish)
      dur_mod    = 1 - (defender.durability / 15)  (tougher dinos resist)
      xf_mod     = 1 + attacker.xfactor / 30  (clutch factor)

      chance = base * damage_mod * round_mod * dur_mod * xf_mod

    Typical values:
      Round 1, defender at 95 HP, dur 10: ~0.04%  (very rare)
      Round 5, defender at 60 HP, dur 5:  ~4.5%   (plausible)
      Round 7, defender at 40 HP, dur 5:  ~8.5%   (real threat)
    """
    if defender.hp >= 85:
        return None  # can't finish someone who's barely been touched
    if damage_dealt < 1.5:
        return None  # need a meaningful hit to trigger a finish

    base = 0.10
    damage_mod = (100.0 - defender.hp) / 100.0
    round_mod = round_num / max_rounds
    dur_mod = 1.0 - (defender.durability / 15.0)  # dur 10 → 0.33, dur 5 → 0.67
    xf_mod = 1.0 + (attacker.xfactor / 30.0)      # xf 9 → 1.30, xf 4 → 1.13

    chance = base * damage_mod * round_mod * dur_mod * xf_mod

    if random.random() < chance:
        return _finish_method(attacker)
    return None


# ----- Exchange -----

def _exchange(
    attacker: Dino,
    defender: Dino,
    round_num: int,
    max_rounds: int,
    log: list[str],
    round_log: list[str],
    exchanges: list[Exchange],
) -> tuple[str, Dino, Dino] | None:
    """Run one exchange. Returns (method, winner, loser) if match ends, else None."""
    if defender.counters():
        off = defender.offense_roll() * 0.65
        dmg = max(1.0, off - attacker.defense / 3.0) * 1.5
        attacker.hp -= dmg
        line = (
            f"    {defender.name} reads it and reverses for {dmg:.1f}."
            f"  [{attacker.name} HP {attacker.hp:.1f}]"
        )
        log.append(line)
        round_log.append(line)
        exchanges.append(Exchange(kind="counter", by=defender.slug, to=attacker.slug, damage=round(dmg, 1)))

        # Defender dealt the damage → defender is the potential finisher.
        if attacker.hp <= 0:
            return ("ko", defender, attacker)
        finish = _check_finish(defender, attacker, round_num, max_rounds, dmg)
        if finish:
            return (finish, defender, attacker)
    else:
        off = attacker.offense_roll()
        dfn = defender.defense_roll()
        dmg = max(1.0, off - dfn) * 1.6
        defender.hp -= dmg
        line = (
            f"    {attacker.name} lands for {dmg:.1f}."
            f"  [{defender.name} HP {defender.hp:.1f}]"
        )
        log.append(line)
        round_log.append(line)
        exchanges.append(Exchange(kind="strike", by=attacker.slug, to=defender.slug, damage=round(dmg, 1)))

        # Attacker dealt the damage → attacker is the potential finisher.
        if defender.hp <= 0:
            return ("ko", attacker, defender)
        finish = _check_finish(attacker, defender, round_num, max_rounds, dmg)
        if finish:
            return (finish, attacker, defender)
    return None


# ----- Main sim loop -----

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
    finish_round: int | None = None
    early_exit = False
    winner: Dino | None = None
    loser: Dino | None = None

    for r in range(1, max_rounds + 1):
        log.append(f"[Round {r}]")
        round_log: list[str] = [f"[Round {r}]"]
        exchanges: list[Exchange] = []

        first, second = (a, b) if random.random() < 0.5 else (b, a)

        # Exchange 1
        result = _exchange(first, second, r, max_rounds, log, round_log, exchanges)
        if result:
            m, w, l = result
            _finish_line(w, l, m, r, log, round_log, exchanges)
            rounds.append(RoundResult(round=r, exchanges=exchanges,
                                       hp={a.slug: round(a.hp, 1), b.slug: round(b.hp, 1)},
                                       narration="\n".join(round_log)))
            winner, loser, method, finish_round, early_exit = w, l, m, r, True
            break

        # Exchange 2
        result = _exchange(second, first, r, max_rounds, log, round_log, exchanges)
        if result:
            m, w, l = result
            _finish_line(w, l, m, r, log, round_log, exchanges)
            rounds.append(RoundResult(round=r, exchanges=exchanges,
                                       hp={a.slug: round(a.hp, 1), b.slug: round(b.hp, 1)},
                                       narration="\n".join(round_log)))
            winner, loser, method, finish_round, early_exit = w, l, m, r, True
            break

        # Interference check
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
                    winner, loser, method, finish_round, early_exit = other, target, "interference", r, True
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

    assert winner is not None and loser is not None
    return MatchData(
        dinos=(a, b),
        rounds=rounds,
        winner=winner,
        loser=loser,
        method=method,
        finish_round=finish_round,
        log=log,
    )


def _finish_line(
    winner: Dino, loser: Dino, method: str, r: int,
    log: list[str], round_log: list[str], exchanges: list[Exchange],
) -> None:
    """Append the finish announcement to the logs."""
    labels = {
        "ko": "KO",
        "tko": "TKO (referee stoppage)",
        "submission": "SUBMISSION",
    }
    label = labels.get(method, method.upper())
    line = f">>> {label}: {winner.name} finishes {loser.name} in round {r}! <<<"
    log.append(line)
    round_log.append(line)
    exchanges.append(Exchange(kind="finish", by=winner.slug, to=loser.slug, damage=0, note=label))
