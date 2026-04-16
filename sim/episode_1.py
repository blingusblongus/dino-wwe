"""Episode 1 — 'The Kingston Dynasty'

Default mode: prints simulation output to stdout (useful for inspection).

--write mode: emits data/shows/ep1/runsheet.json + match_<n>.json so the
Go showrunner can broadcast events on a wall-clock timeline.

Vignette-driven mods (pre-match):
- "You'll touch this belt Friday. Not before." (cold open):
    Anky motivation +1 (humiliation fuels him).
- Mendoza slips Dilo a vial before the opener:
    Dilo confidence +1 (chemical courage).
- The Emperor's briefcase offer (mid-show backstage):
    Sets up scripted interference check in main event.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from roster import fresh_roster
from sim import simulate
from writer import Match, TimingConfig, Vignette, write_show


SHOW_ID = "ep1"
SHOW_TITLE = "WDAA Episode 1 — The Kingston Dynasty"


def build_plan() -> tuple[list, dict]:
    """Returns (plan, dinos). dinos is the post-vignette-mod roster."""
    d = fresh_roster()

    # --- Pre-match vignette mods ---
    d["anky"].motivation += 1     # Cold open backstage humiliation
    d["dilo"].confidence += 1     # Mendoza's vial

    plan = [
        Vignette(
            title="Cold Open — Backstage",
            text=(
                "Anky Bronson tapes his wrists. Rex Kingston rolls up with "
                "The Emperor. Rex shoves the Apex belt in Anky's face. The "
                "Emperor snatches it back. \"You'll touch this belt Friday. "
                "Not before.\" Anky says nothing."
            ),
        ),
        Match(
            match_id="ep1-m1",
            title="Velo Machado vs. Dilo DeVille (Opener)",
            a=d["velo"], b=d["dilo"],
            seed=42,
        ),
        Vignette(
            title="Backstage — The Emperor's Briefcase",
            text=(
                "The Emperor walks into Dilo DeVille's locker room with a "
                "briefcase. The door closes. We hear it open. We hear a "
                "whistle. We hear it close. The Emperor walks out lighter."
            ),
        ),
        Match(
            match_id="ep1-m2",
            title="Rex Kingston (c) vs. Anky Bronson — WDAA Apex Championship",
            a=d["rex"], b=d["anky"],
            seed=7,
            interference={
                "round": 4,
                "chance": 0.65,
                "actor": "Dilo DeVille",
                "target": d["anky"],
                "damage": 18.0,
            },
        ),
        Vignette(
            title="Closer — Parking Lot",
            text=(
                "Two identical briefcases on a limo's roof. The Emperor "
                "demands his back. Dilo: \"Which one, Emperor? This one's "
                "the payment. This one's the evidence.\" The limo drives off."
            ),
        ),
    ]
    return plan, d


def main() -> None:
    ap = argparse.ArgumentParser(description="Run Episode 1.")
    ap.add_argument("--write", action="store_true",
                    help="Emit runsheet.json + match files instead of printing.")
    ap.add_argument("--out-dir", default="/data",
                    help="Where to write data (default: /data, suitable for container bind-mount).")
    ap.add_argument("--starts-in", type=int, default=30,
                    help="Seconds from now until the show begins (default: 30).")
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

    # --- Default: print mode (legacy behaviour) ---
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
