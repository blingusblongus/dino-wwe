"""Episode 1 — 'The Kingston Dynasty'

Applies pre-match stat mods driven by this week's vignettes, then runs the
two matches. Writes match logs to stdout.

Vignette-driven mods (pre-match):
- "You'll touch this belt Friday. Not before." (cold open):
    Anky motivation +1 (humiliation fuels him).
- Mendoza slips Dilo a vial before the opener:
    Dilo confidence +1 (chemical courage).
- The Emperor's briefcase offer (mid-show backstage):
    No stat change — sets up scripted interference check in main event.
"""

import subprocess
import sys

from roster import fresh_roster
from sim import simulate


def main() -> None:
    d = fresh_roster()

    # === Pre-match vignette mods ===
    d["anky"].motivation += 1     # Cold open backstage humiliation
    d["dilo"].confidence += 1     # Mendoza's vial

    print("=" * 60)
    print("WDAA EPISODE 1 — THE KINGSTON DYNASTY")
    print("=" * 60)

    print("\n[Stat card — post-vignette, pre-match]")
    for k in ("rex", "velo", "anky", "dilo"):
        e = d[k]
        print(
            f"  {e.name:<18} POW {e.power} DUR {e.durability} DEF {e.defense} "
            f"BRA {e.brains} XF {e.xfactor} | CONF {e.confidence} MOT {e.motivation}"
        )

    # === Match 1: Opener ===
    print("\n\n--- MATCH 1 — Velo Machado vs. Dilo DeVille ---")
    w1, l1, log1 = simulate(d["velo"], d["dilo"], seed=42)
    print("\n".join(log1))

    # === Match 2: Main Event ===
    # The Emperor paid Dilo for a potential run-in. Dilo is chaos — the
    # probability reflects whether he actually does what he was paid for.
    # Dilo confidence is high this week (vial); that nudges the chance up.
    print("\n\n--- MAIN EVENT — Rex Kingston (c) vs. Anky Bronson ---")
    print("               WDAA Apex Championship")
    w2, l2, log2 = simulate(
        d["rex"], d["anky"], seed=7,
        interference={
            "round": 4,
            "chance": 0.65,
            "actor": "Dilo DeVille",
            "target": d["anky"],
            "damage": 18.0,
        },
    )
    print("\n".join(log2))

    # === Result summary for narrative authoring ===
    print("\n\n=== EPISODE 1 RESULTS ===")
    print(f"  Opener winner:     {w1.name} (HP {w1.hp:.1f} vs {l1.name} {l1.hp:.1f})")
    print(f"  Main event winner: {w2.name} (HP {w2.hp:.1f} vs {l2.name} {l2.hp:.1f})")


if __name__ == "__main__":
    main()
