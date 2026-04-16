"""WDAA match simulator (POC v0.1).

Hybrid model: the sim decides outcomes probabilistically from stats + mental state.
Narrative is authored separately. Stats range 1-10. Mental stats (confidence,
motivation) fluctuate episode-to-episode based on vignettes and match results.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class Dino:
    name: str
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


def exchange(attacker: Dino, defender: Dino, log: list[str]) -> None:
    if defender.counters():
        off = defender.offense_roll() * 0.65
        dmg = max(0.0, off - attacker.defense / 3.0) * 1.2
        attacker.hp -= dmg
        log.append(
            f"    {defender.name} reads it and reverses for {dmg:.1f}."
            f"  [{attacker.name} HP {attacker.hp:.1f}]"
        )
    else:
        off = attacker.offense_roll()
        dfn = defender.defense_roll()
        dmg = max(0.0, off - dfn) * 1.25
        defender.hp -= dmg
        log.append(
            f"    {attacker.name} lands for {dmg:.1f}."
            f"  [{defender.name} HP {defender.hp:.1f}]"
        )


def simulate(
    a: Dino,
    b: Dino,
    *,
    max_rounds: int = 7,
    seed: int | None = None,
    interference: dict | None = None,
) -> tuple[Dino, Dino, list[str]]:
    """Simulate a match. Returns (winner, loser, log).

    interference: optional dict describing a scripted run-in check.
      {round: int, chance: float, actor: str, target: Dino, damage: float}
    """
    if seed is not None:
        random.seed(seed)
    a.hp = b.hp = 100.0
    log = [f"=== {a.name} vs. {b.name} ==="]

    for r in range(1, max_rounds + 1):
        log.append(f"[Round {r}]")
        first, second = (a, b) if random.random() < 0.5 else (b, a)
        exchange(first, second, log)
        if second.hp <= 0:
            log.append(f">>> KO: {first.name} wins in round {r}. <<<")
            return first, second, log
        exchange(second, first, log)
        if first.hp <= 0:
            log.append(f">>> KO: {second.name} wins in round {r}. <<<")
            return second, first, log

        if interference and r == interference["round"]:
            if random.random() < interference["chance"]:
                interference["target"].hp -= interference["damage"]
                log.append(
                    f"    >>> INTERFERENCE: {interference['actor']} strikes "
                    f"{interference['target'].name} for {interference['damage']:.1f}. <<<"
                    f"  [HP {interference['target'].hp:.1f}]"
                )
                if interference["target"].hp <= 0:
                    other = a if interference["target"] is b else b
                    log.append(
                        f">>> {other.name} wins in round {r} after outside interference. <<<"
                    )
                    return other, interference["target"], log
            else:
                log.append(
                    f"    (Interference threatened by {interference['actor']} "
                    f"but never materialized.)"
                )

    winner, loser = (a, b) if a.hp > b.hp else (b, a)
    log.append(
        f">>> DECISION: {winner.name} ({winner.hp:.1f}) defeats "
        f"{loser.name} ({loser.hp:.1f}). <<<"
    )
    return winner, loser, log
