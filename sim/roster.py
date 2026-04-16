"""WDAA roster — season 1, episode 1 baseline stats.

Stats are 1-10. Physical stats (power/durability/defense/brains/xfactor) are
stable. Mental stats (confidence/motivation) drift with story events.

Character sketches and season feuds live in roster.md — this file is the
numeric source of truth for the sim.
"""

from sim import Dino


def fresh_roster() -> dict[str, Dino]:
    return {
        # REIGNING APEX CHAMPION. Nepo-baby heel. Born on third base, thinks
        # he hit a triple. Coasts on pedigree — hence high confidence, soft
        # motivation.
        "rex": Dino(
            name="Rex Kingston",
            species="Tyrannosaurus rex",
            power=9, durability=9, defense=6, brains=4, xfactor=6,
            confidence=10, motivation=6,
        ),
        # TOP CONTENDER-IN-WAITING. Cocky technician, ex-pack alpha turned
        # solo act. Rock-tier mic. Tweener crowd eats him up.
        "velo": Dino(
            name="Velo Machado",
            species="Velociraptor",
            power=6, durability=5, defense=7, brains=9, xfactor=8,
            confidence=8, motivation=8,
        ),
        # #1 CONTENDER, TITLE SHOT EARNED. Blue-collar face. Walking tank,
        # chip on his armored shoulder. The People's Tank.
        "anky": Dino(
            name="Anky Bronson",
            species="Ankylosaurus",
            power=7, durability=10, defense=9, brains=5, xfactor=4,
            confidence=6, motivation=9,
        ),
        # CHAOS AGENT. Evil-genius heel with a manager (Dr. Mendoza) and
        # a rumored stable in the wings. Will cheat, will spit venom, will
        # accept cash from anyone.
        "dilo": Dino(
            name="Dilo DeVille",
            species="Dilophosaurus",
            power=5, durability=6, defense=7, brains=8, xfactor=9,
            confidence=7, motivation=7,
        ),
    }
