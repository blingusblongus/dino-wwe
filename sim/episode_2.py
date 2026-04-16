"""Episode 2 — 'Evidence'

Carries stat deltas forward from Episode 1 and applies Week 2 vignette mods.

Post-Ep1 mental deltas:
  Rex:  CONF 10->9, MOT 6->7
  Velo: CONF 8->6, MOT 8->10
  Anky: CONF 6->8, MOT 9->10 (cap)
  Dilo: CONF 7->10 (cap), MOT 7->9

Week 2 vignette mods:
  - Dilo opens the "evidence" briefcase on air in the cold open. Photos of
    The Emperor's previous payoffs going back years. Emperor CONF -2 (not
    a wrestler but this matters for one of the calls later — ignored here).
    Rex CONF -1 (his dad's name is on every document).
  - Velo catches Dilo alone backstage and proposes an alliance. Dilo
    laughs. Velo's MOT +1 (rejection fuels him).
  - Anky cuts his first-ever promo — short, cold, points at Rex. Anky
    CONF +1 (mic presence unlocked).
  - The Emperor, desperate, announces a #1 contender's match NEXT week
    (Velo vs Anky) with the winner getting Rex at the PPV. Not this
    episode — but frames the main event: Rex must defend against DILO,
    who used the evidence to blackmail a title shot.

Matches this week:
  Match 1: Anky Bronson vs. Velo Machado — #1 contender's match.
  Main: Rex Kingston (c) vs. Dilo DeVille — impromptu title defense
        forced by blackmail.
"""

from roster import fresh_roster
from sim import simulate


def main() -> None:
    d = fresh_roster()

    # === Carry-forward from Episode 1 ===
    d["rex"].confidence = 9;  d["rex"].motivation = 7
    d["velo"].confidence = 6; d["velo"].motivation = 10
    d["anky"].confidence = 8; d["anky"].motivation = 10
    d["dilo"].confidence = 10; d["dilo"].motivation = 9

    # === Episode 2 vignette mods ===
    d["rex"].confidence -= 1   # Evidence reveal — his father's name on papers
    d["velo"].motivation = min(10, d["velo"].motivation + 1)  # Rejected by Dilo
    d["anky"].confidence += 1  # Cut his first real promo

    print("=" * 60)
    print("WDAA EPISODE 2 — EVIDENCE")
    print("=" * 60)

    print("\n[Stat card — post-vignette, pre-match]")
    for k in ("rex", "velo", "anky", "dilo"):
        e = d[k]
        print(
            f"  {e.name:<18} POW {e.power} DUR {e.durability} DEF {e.defense} "
            f"BRA {e.brains} XF {e.xfactor} | CONF {e.confidence} MOT {e.motivation}"
        )

    # === Match 1: #1 Contender's match ===
    print("\n\n--- MATCH 1 — Anky Bronson vs. Velo Machado ---")
    print("               #1 Contender's Match (winner gets Rex at Paleozoic PPV)")
    w1, l1, log1 = simulate(d["anky"], d["velo"], seed=11)
    print("\n".join(log1))

    # === Main Event: Blackmail-forced title defense ===
    # Dilo has leverage. Rex is on tilt. The Emperor is banned from ringside
    # (Dilo's demand). No interference scripted — Dilo doesn't need it.
    print("\n\n--- MAIN EVENT — Rex Kingston (c) vs. Dilo DeVille ---")
    print("               WDAA Apex Championship — Emperor barred from ringside")
    w2, l2, log2 = simulate(d["rex"], d["dilo"], seed=99)
    print("\n".join(log2))

    print("\n\n=== EPISODE 2 RESULTS ===")
    print(f"  Contender's match winner: {w1.name} (HP {w1.hp:.1f} vs {l1.name} {l1.hp:.1f})")
    print(f"  Main event winner:        {w2.name} (HP {w2.hp:.1f} vs {l2.name} {l2.hp:.1f})")


if __name__ == "__main__":
    main()
