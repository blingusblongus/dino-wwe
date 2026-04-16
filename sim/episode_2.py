"""Episode 2 — 'Evidence'

Carries stat deltas forward from Episode 1 and applies Week 2 vignette mods.

Default mode: prints simulation output to stdout.
--write mode: emits data/shows/ep2/runsheet.json + match files.

Post-Ep1 mental deltas:
  Rex:  CONF 10->9, MOT 6->7
  Velo: CONF 8->6, MOT 8->10
  Anky: CONF 6->8, MOT 9->10 (cap)
  Dilo: CONF 7->10 (cap), MOT 7->9

Week 2 vignette mods:
  - Evidence-briefcase reveal: Rex CONF -1 (his father's name is on the papers).
  - Velo proposes alliance, Dilo laughs: Velo MOT +1 (rejection fuels him).
  - Anky cuts his first real promo: Anky CONF +1 (mic presence unlocked).

Matches this week:
  Match 1: Anky Bronson vs. Velo Machado — #1 contender's match.
  Main:    Rex Kingston (c) vs. Dilo DeVille — impromptu title defense
           forced by blackmail.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from roster import fresh_roster
from sim import simulate
from writer import Match, TimingConfig, Vignette, write_show


SHOW_ID = "ep2"
SHOW_TITLE = "WDAA Episode 2 — Evidence"


def build_plan() -> tuple[list, dict]:
    d = fresh_roster()

    # --- Carry-forward from Episode 1 ---
    d["rex"].confidence, d["rex"].motivation = 9, 7
    d["velo"].confidence, d["velo"].motivation = 6, 10
    d["anky"].confidence, d["anky"].motivation = 8, 10
    d["dilo"].confidence, d["dilo"].motivation = 10, 9

    # --- Episode 2 vignette mods ---
    d["rex"].confidence -= 1
    d["velo"].motivation = min(10, d["velo"].motivation + 1)
    d["anky"].confidence += 1

    plan = [
        Vignette(
            title="Cold Open — The Evidence Briefcase",
            text=(
                "Dilo DeVille opens a briefcase live on air. Inside: a stack "
                "of photos. The Emperor paying off referees, judges, and "
                "fighters going back fifteen years. King Rex Sr.'s name on "
                "every document. Dilo demands an impromptu title shot."
            ),
        ),
        Match(
            match_id="ep2-m1",
            title="Anky Bronson vs. Velo Machado — #1 Contender's Match",
            a=d["anky"], b=d["velo"],
            seed=11,
        ),
        Vignette(
            title="Backstage — The Alliance That Didn't Happen",
            text=(
                "Velo Machado corners Dilo by catering. Proposes an alliance. "
                "Dilo: \"Velo, I beat you with cough syrup in my stomach. "
                "Earn it.\" Velo stands alone in the corridor."
            ),
        ),
        Vignette(
            title="Anky's First Promo",
            text=(
                "Anky Bronson, by the locker room sinks, looks directly into "
                "a camera for the first time. \"I earned my shot. I'm going "
                "to keep it.\" Cut to black for half a second."
            ),
        ),
        Match(
            match_id="ep2-m2",
            title="Rex Kingston (c) vs. Dilo DeVille — WDAA Apex Championship (Emperor barred)",
            a=d["rex"], b=d["dilo"],
            seed=99,
        ),
        Vignette(
            title="Closing — The Stable Reveal",
            text=(
                "Mendoza on the mic: \"On behalf of OUR faction — let me "
                "introduce the other two.\" Two silhouettes at the top of "
                "the ramp. One tall. One small. Cut to black."
            ),
        ),
    ]
    return plan, d


def main() -> None:
    ap = argparse.ArgumentParser(description="Run Episode 2.")
    ap.add_argument("--write", action="store_true",
                    help="Emit runsheet.json + match files instead of printing.")
    ap.add_argument("--out-dir", default="/data",
                    help="Where to write data (default: /data).")
    ap.add_argument("--starts-in", type=int, default=30,
                    help="Seconds from now until the show begins.")
    ap.add_argument("--round-seconds", type=int, default=10,
                    help="Wall-clock seconds between successive rounds.")
    ap.add_argument("--vignette-seconds", type=int, default=25,
                    help="Wall-clock seconds a vignette is given before the next item.")
    args = ap.parse_args()

    plan, _ = build_plan()

    if args.write:
        starts_at = datetime.now(timezone.utc) + timedelta(seconds=args.starts_in)
        timing = TimingConfig(
            vignette_seconds=args.vignette_seconds,
            round_seconds=args.round_seconds,
        )
        result = write_show(
            out_dir=args.out_dir,
            show_id=SHOW_ID,
            title=SHOW_TITLE,
            starts_at=starts_at,
            plan=plan,
            timing=timing,
        )
        print(f"wrote runsheet: {result.runsheet_path}")
        for p in result.match_paths:
            print(f"wrote match:    {p}")
        print(f"show window:    {result.starts_at.isoformat()} → {result.ends_at.isoformat()}")
        print(f"events:         {result.n_events}")
        return

    # --- Default: print mode ---
    print("=" * 60)
    print(SHOW_TITLE)
    print("=" * 60)
    for item in plan:
        if isinstance(item, Vignette):
            print(f"\n[VIGNETTE] {item.title}")
            if item.text:
                print(f"  {item.text}")
        elif isinstance(item, Match):
            print(f"\n--- {item.title} ---")
            data = simulate(item.a, item.b, seed=item.seed, interference=item.interference)
            print("\n".join(data.log))


if __name__ == "__main__":
    main()
