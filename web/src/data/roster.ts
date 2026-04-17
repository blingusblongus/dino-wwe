export interface Dino {
  slug: string;
  name: string;
  epithet: string;
  species: string;
  alignment: "Face" | "Heel" | "Tweener";
  title?: string;
  description: string;
  signature: string;
  finisher: string;
  stats: {
    pow: number; dur: number; def: number;
    bra: number; xf: number; conf: number; mot: number;
  };
}

export const roster: Dino[] = [
  {
    slug: "rex",
    name: "Rex Kingston",
    epithet: "The Apex",
    species: "Tyrannosaurus rex",
    alignment: "Heel",
    title: "Reigning WDAA Apex Champion (413 days)",
    description:
      "Son of legendary retired champion King Rex Sr. (\"The Emperor\"), who now manages " +
      "him from ringside. Treats the title like a family heirloom. Doesn't train. Doesn't " +
      "have to — he's a Kingston.",
    signature: "Dynastic Chomp (fall-away biting suplex)",
    finisher: "Extinction Event (tail-assisted powerbomb)",
    stats: { pow: 9, dur: 9, def: 6, bra: 4, xf: 6, conf: 10, mot: 6 },
  },
  {
    slug: "velo",
    name: "Velo Machado",
    epithet: "The Final Cut",
    species: "Velociraptor",
    alignment: "Tweener",
    description:
      "Broke from his pack two years ago after a public falling-out with his brothers. " +
      "Fastest hands in the WDAA. Fans cheer because he's cool, not because he's kind.",
    signature: "The Pack Attack (blinding six-strike combo)",
    finisher: "The Final Cut (sickle-claw DDT off the top rope)",
    stats: { pow: 6, dur: 5, def: 7, bra: 9, xf: 8, conf: 8, mot: 8 },
  },
  {
    slug: "anky",
    name: "Anky Bronson",
    epithet: "The People's Tank",
    species: "Ankylosaurus",
    alignment: "Face",
    description:
      "Blue-collar. Fought his way up from the Cretaceous indies. His father worked " +
      "security at Emperor's matches for thirty years and got stiffed on his pension. " +
      "Carries that bill into every fight.",
    signature: "Blue-Collar Barrage (running body check into short-arm chops)",
    finisher: "The Wrecking Ball (full-rotation tail lariat)",
    stats: { pow: 7, dur: 10, def: 9, bra: 5, xf: 4, conf: 6, mot: 9 },
  },
  {
    slug: "dilo",
    name: "Dilo DeVille",
    epithet: "The Venom",
    species: "Dilophosaurus",
    alignment: "Heel",
    description:
      "Flanked by his manager Dr. Mendoza and his briefcase nobody has ever opened. " +
      "Uses toxic spit that is technically illegal but functionally un-refereeable. " +
      "Has dropped hints about \"the other two.\" Nobody knows what he means. Yet.",
    signature: "The Mendoza Line (manager distraction into blinding spit)",
    finisher: "The Venom Kiss (sleeper with venom seep — knockout)",
    stats: { pow: 5, dur: 6, def: 7, bra: 8, xf: 9, conf: 7, mot: 7 },
  },
];
