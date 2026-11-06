"""The verifier's own copy of src/plugin/progression.py, kept identical below the imports: the
chart's harmony in the abstract (scale degrees, alterations, chord suffixes and bass notes), drawn
from a seed. It names no note: the verifier spells it on the line of fifths, the tools with letters
and semitones.

A chord is a dict:
  degree  0-6, the scale degree of its root (0 is the tonic)
  alter   -1, 0 or 1: the root lowered or raised a semitone from the scale
  kind    maj, min, dim, dom or aug: what its third (and fifth) are
  suffix  the symbol after the root, e.g. "m7", "maj7#11"
  bass    None; "third" or "fifth", the chord's own third or fifth; or [degree, alter], a scale
          degree (altered) under it
"""

from .rng import Stream

# The keys of each mode, in the order a seed picks from.
MAJOR_KEYS = ["C", "G", "D", "A", "E", "B", "F#", "C#", "F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb"]
MINOR_KEYS = ["Am", "Em", "Bm", "F#m", "C#m", "G#m", "D#m", "A#m", "Dm", "Gm", "Cm", "Fm", "Bbm", "Ebm", "Abm"]
TRIADS = {
    "major": ["maj", "min", "min", "maj", "maj", "min", "dim"],
    "minor": ["min", "dim", "maj", "min", "min", "maj", "maj"],
}
SUFFIXES = {
    "maj": ["", "", "maj7", "6", "add9", "sus2", "sus4", "maj7#11"],
    "min": ["m", "m", "m7", "m6"],
    "dim": ["dim", "m7b5", "dim7"],
    "dom": ["7", "7", "9", "13", "7sus4", "7b9", "7#11"],
    "aug": ["aug"],
}
# Degrees a secondary dominant may lead to (never the tonic or a diminished chord).
TONICIZED = {"major": [1, 2, 3, 4, 5], "minor": [2, 3, 4, 5, 6]}
# Borrowed chords: (degree, alter, kind).
BORROWED = {
    "major": [[6, -1, "maj"], [5, -1, "maj"], [3, 0, "min"]],
    "minor": [[4, 0, "dom"], [3, 0, "maj"], [1, -1, "maj"]],
}
# A chromatic bass under the tonic chord: [degree, alter].
TONIC_BASS = {"major": [6, -1], "minor": [5, 1]}


def mode_of(key):
    return "minor" if key.endswith("m") else "major"


def source_key(seed, to_key):
    """The key the chart is written in: a key of to_key's mode, possibly to_key itself."""
    keys = MINOR_KEYS if mode_of(to_key) == "minor" else MAJOR_KEYS
    return keys[Stream("chord-key", f"{seed}|{to_key}").below(len(keys))]


def progression(seed, key):
    """The chart's bars, each a list of 1 or 2 abstract chords."""
    mode = mode_of(key)
    stream = Stream("chord-chart", f"{seed}|{key}")
    bars = []
    for bar in range(stream.between(8, 16)):
        chords = []
        for slot in range(2 if stream.chance(1, 3) else 1):
            chords.append(chord(stream, mode, first=bar == 0 and slot == 0))
        bars.append(chords)
    return bars


def chord(stream, mode, first):
    pick = 0 if first else stream.below(100)
    if pick < 55:
        degree = 0 if first else stream.below(7)
        alter, kind = 0, TRIADS[mode][degree]
    elif pick < 70:
        degree, alter, kind = (stream.choice(TONICIZED[mode]) + 4) % 7, 0, "dom"
    elif pick < 85:
        degree, alter, kind = stream.choice(BORROWED[mode])
    else:
        degree, alter, kind = (0 if mode == "major" else 2), 0, "aug"
    suffix = stream.choice(SUFFIXES[kind])
    bass = None
    if kind in ("maj", "min", "dom") and "sus" not in suffix and stream.chance(1, 5):
        bass = stream.choice(["third", "fifth"])
    elif degree == 0 and alter == 0 and kind in ("maj", "min") and stream.chance(1, 8):
        bass = list(TONIC_BASS[mode])
    return {"degree": degree, "alter": alter, "kind": kind, "suffix": suffix, "bass": bass}
