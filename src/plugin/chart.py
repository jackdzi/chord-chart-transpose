"""Notes as (letter, semitone) pairs, the charts, their transposition, and the three tools."""

from __future__ import annotations

import re
from pathlib import Path

from contract import Bar, ChartInput, ChartOutput, Key, KeyInput, KeyOutput, Mode, PinOutput
from plugin.progression import mode_of, progression, source_key
from plugin.rng import canonical_sha256

LETTERS = "CDEFGAB"
NATURAL = [0, 2, 4, 5, 7, 9, 11]  # each letter's semitone above C
STEPS = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10]}
CHORD = re.compile(r"^([A-G][#b]?)([^/#b][^/]*|)(?:/([A-G][#b]?))?$")
MAX_SEED = 1_000_000_000


def spell(letter: int, pitch: int) -> str:
    """The note on letter index ``letter`` sounding ``pitch`` (mod 12). A double sharp moves to the next
    letter up and a double flat to the next letter down, until one accidental or none remains."""
    letter %= 7
    while True:
        accidental = (pitch - NATURAL[letter] + 6) % 12 - 6
        if accidental >= 2:
            letter = (letter + 1) % 7
        elif accidental <= -2:
            letter = (letter - 1) % 7
        else:
            return LETTERS[letter] + ("#" if accidental == 1 else "b" if accidental == -1 else "")


def parse_note(note: str) -> tuple[int, int]:
    """(letter index, pitch) of a note such as F#, Bb or E."""
    letter = LETTERS.index(note[0])
    return letter, (NATURAL[letter] + note.count("#") - note.count("b")) % 12


def move(note: str, letters: int, semitones: int) -> str:
    """``note`` moved up ``letters`` letters and ``semitones`` semitones, spelled by :func:`spell`."""
    letter, pitch = parse_note(note)
    return spell(letter + letters, pitch + semitones)


def tonic(key: str) -> str:
    return key[:-1] if mode_of(key) == "minor" else key


def scale(key: str) -> list[str]:
    letter, pitch = parse_note(tonic(key))
    return [spell(letter + i, pitch + step) for i, step in enumerate(STEPS[mode_of(key)])]


def signature(key: str) -> int:
    return sum(note.count("#") - note.count("b") for note in scale(key))


def spell_chord(key: str, chord: dict) -> str:
    """An abstract chord (see plugin.progression) written in ``key``."""
    degree = scale(key)[chord["degree"]]
    letter, pitch = parse_note(degree)
    root = spell(letter, pitch + chord["alter"])
    bass = chord["bass"]
    if bass == "third":
        bass_note = move(root, 2, 4 if chord["kind"] in ("maj", "dom", "aug") else 3)
    elif bass == "fifth":
        bass_note = move(root, 4, 7)
    elif bass is not None:
        letter, pitch = parse_note(scale(key)[bass[0]])
        bass_note = spell(letter, pitch + bass[1])
    return root + chord["suffix"] + (f"/{bass_note}" if bass is not None else "")


def interval(source: str, target: str) -> tuple[int, int]:
    """(letters, semitones) up from the source key's tonic to the target key's."""
    (source_letter, source_pitch), (target_letter, target_pitch) = parse_note(tonic(source)), parse_note(tonic(target))
    return (target_letter - source_letter) % 7, (target_pitch - source_pitch) % 12


def transpose_chord(symbol: str, letters: int, semitones: int) -> str:
    match = CHORD.fullmatch(symbol)
    if match is None:
        raise ValueError(f"not a chord symbol: {symbol!r}")
    root, suffix, bass = match.groups()
    moved = move(root, letters, semitones) + suffix
    return moved + (f"/{move(bass, letters, semitones)}" if bass else "")


def chart(task: ChartInput) -> tuple[str, list[list[str]]]:
    """The task's source key and its bars of chord symbols."""
    if not 0 <= task.seed <= MAX_SEED:
        raise ValueError(f"seed must be from 0 to {MAX_SEED}")
    key = source_key(task.seed, task.to_key.value)
    return key, [[spell_chord(key, c) for c in bar] for bar in progression(task.seed, key)]


def get_chart(task: ChartInput, workspace: Path) -> ChartOutput:
    key, bars = chart(task)
    letters, semitones = interval(key, task.to_key.value)
    return ChartOutput(
        source_key=Key(key),
        to_key=task.to_key,
        letter_steps=letters,
        semitones=semitones,
        chords=sum(len(bar) for bar in bars),
        bars=[Bar(chords=bar) for bar in bars],
    )


def key_info(given: KeyInput, workspace: Path) -> KeyOutput:
    key = given.key.value
    return KeyOutput(key=given.key, mode=Mode(mode_of(key)), scale=scale(key), signature=signature(key))


def pin_transposition(task: ChartInput, workspace: Path) -> PinOutput:
    key, bars = chart(task)
    letters, semitones = interval(key, task.to_key.value)
    moved = [[transpose_chord(symbol, letters, semitones) for symbol in bar] for bar in bars]
    return PinOutput(
        chart_sha256=canonical_sha256({"source_key": key, "bars": bars}),
        source_key=Key(key),
        source_bars=[Bar(chords=bar) for bar in bars],
        bars=[Bar(chords=bar) for bar in moved],
    )
