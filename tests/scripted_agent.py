"""A scripted stand-in for the agent: it follows the task's instructions with no model, so a whole
run can be replayed offline. It reads only what get_chart returns."""

from __future__ import annotations

LETTERS = "CDEFGAB"
NATURAL = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def move_note(note: str, letter_steps: int, semitones: int) -> str:
    """Move the letter up letter_steps and the pitch up semitones, then fix the accidental."""
    letter = LETTERS[(LETTERS.index(note[0]) + letter_steps) % 7]
    pitch = (NATURAL[note[0]] + note.count("#") - note.count("b") + semitones) % 12
    while True:
        offset = (pitch - NATURAL[letter]) % 12
        if offset == 0:
            return letter
        if offset == 1:
            return letter + "#"
        if offset == 11:
            return letter + "b"
        # A double (or worse) accidental: move to the next letter toward the pitch.
        step = 1 if offset < 6 else -1
        letter = LETTERS[(LETTERS.index(letter) + step) % 7]


def transpose(symbol: str, letter_steps: int, semitones: int) -> str:
    chord, _, bass = symbol.partition("/")
    root_length = 2 if len(chord) > 1 and chord[1] in "#b" else 1
    moved = move_note(chord[:root_length], letter_steps, semitones) + chord[root_length:]
    return moved + (f"/{move_note(bass, letter_steps, semitones)}" if bass else "")


def submission(chart: dict) -> dict:
    """The task output for a get_chart result (as JSON)."""
    steps, semitones = chart["letter_steps"], chart["semitones"]
    return {
        "to_key": chart["to_key"],
        "bars": [{"chords": [transpose(symbol, steps, semitones) for symbol in bar["chords"]]} for bar in chart["bars"]],
    }
