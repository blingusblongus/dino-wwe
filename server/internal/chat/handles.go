package chat

import (
	"crypto/sha256"
	"encoding/binary"
	"fmt"
)

// Anon handle generation. We derive the handle deterministically from the
// anon cookie value so the same visitor always sees the same name without
// any server-side state.

var adjectives = []string{
	"grumpy", "feral", "smug", "tactical", "haunted", "buttery", "indignant",
	"nostalgic", "jittery", "regal", "smoldering", "pious", "frumpy", "gallant",
	"unbothered", "ornery", "kindly", "sleepy", "flagrant", "dapper", "scuffed",
	"clammy", "petulant", "sturdy", "anxious", "paleozoic", "pluvial", "extant",
	"taciturn", "obstinate",
}

var dinos = []string{
	"trike", "stego", "anky", "raptor", "trex", "bronto", "diplo", "spino",
	"compy", "ptero", "pachy", "iguanodon", "allosaur", "mosasaur", "carno",
	"therizino", "parasaur", "dilo", "ovirap", "deino", "kentro", "amargasaur",
	"corythosaur", "lambeosaur", "hadrosaur", "edmontosaur", "yutyrannus",
	"giganotosaur", "majungasaur", "concavenator",
}

// HandleFor derives a stable display name from a cookie value.
func HandleFor(cookieValue string) string {
	if cookieValue == "" {
		return "anon"
	}
	h := sha256.Sum256([]byte(cookieValue))
	adj := adjectives[binary.BigEndian.Uint32(h[0:4])%uint32(len(adjectives))]
	dino := dinos[binary.BigEndian.Uint32(h[4:8])%uint32(len(dinos))]
	num := binary.BigEndian.Uint32(h[8:12])%900 + 100
	return fmt.Sprintf("%s-%s-%d", adj, dino, num)
}
