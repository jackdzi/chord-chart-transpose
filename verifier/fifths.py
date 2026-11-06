"""The chord-chart verifier. It works on the line of fifths, not on letters and semitones as the tools
do: a note is its place on the line (F -1, C 0, G 1, D 2, A 3, E 4, B 5; a sharp adds 7, a flat
takes 7), a scale degree or interval is a fixed offset on it, and transposing a chart adds the
distance between the two tonics. A note at 13 or more needs a double sharp, and is moved 12 down
(the same pitch, one letter up); one at -9 or less needs a double flat, and is moved 12 up."""

import re

from .checks import result
from .progression import mode_of, progression, source_key
from .rng import canonical_sha256

ORDER = "FCGDAEB"
# Each scale degree's offset from the tonic.
DEGREES = {"major": [0, 2, 4, -1, 1, 3, 5], "minor": [0, 2, -3, -1, 1, -4, -2]}
MAJOR_THIRD, MINOR_THIRD, FIFTH = 4, -3, 1
SYMBOL = re.compile(r"([A-G])(#|b|)([^/]*?)(?:/([A-G])(#|b|))?")
MAX_SEED = 1_000_000_000


def place(letter, accidental):
    return ORDER.index(letter) - 1 + 7 * (1 if accidental == "#" else -1 if accidental == "b" else 0)


def name(position):
    while position >= 13:
        position -= 12
    while position <= -9:
        position += 12
    sharps = (position + 1) // 7
    return ORDER[(position + 1) % 7] + ("#" * sharps if sharps > 0 else "b" * -sharps)


def tonic_place(key):
    note = key[:-1] if mode_of(key) == "minor" else key
    return place(note[0], note[1:])


def written(key, chord):
    """An abstract chord's symbol in ``key``: each note named only once it is placed."""
    degrees = DEGREES[mode_of(key)]
    root = name(tonic_place(key) + degrees[chord["degree"]] + 7 * chord["alter"])
    root_place = place(root[0], root[1:])
    bass = chord["bass"]
    if bass is None:
        return root + chord["suffix"]
    if bass == "third":
        under = root_place + (MAJOR_THIRD if chord["kind"] in ("maj", "dom", "aug") else MINOR_THIRD)
    elif bass == "fifth":
        under = root_place + FIFTH
    else:
        under = tonic_place(key) + degrees[bass[0]] + 7 * bass[1]
    return f"{root}{chord['suffix']}/{name(under)}"


def rebuild(task):
    """The task's source key and bars, from its seed."""
    key = source_key(task.seed, task.to_key.value)
    return key, [[written(key, c) for c in bar] for bar in progression(task.seed, key)]


def transposed(symbol, shift):
    match = SYMBOL.fullmatch(symbol)
    if match is None:
        return None
    letter, accidental, suffix, bass_letter, bass_accidental = match.groups()
    moved = name(place(letter, accidental) + shift) + suffix
    if bass_letter:
        moved += "/" + name(place(bass_letter, bass_accidental) + shift)
    return moved


def answer(task):
    key, bars = rebuild(task)
    shift = tonic_place(task.to_key.value) - tonic_place(key)
    return key, bars, [[transposed(symbol, shift) for symbol in bar] for bar in bars]


def seed_check(task):
    if not 0 <= task.seed <= MAX_SEED:
        return result(False, f"seed must be from 0 to {MAX_SEED}")
    return result(True, "input is valid")


def key_check(value):
    # Every Key member is a key the tools know; nothing more to check.
    return result(True, "input is valid")


def verify_chart_output(task, output):
    key, bars = rebuild(task)
    if output.source_key.value != key or [bar.chords for bar in output.bars] != bars:
        return result(False, "the chart is not the one the seed gives")
    if mode_of(key) != mode_of(output.to_key.value) or output.to_key is not task.to_key:
        return result(False, "the target key is not the task's")
    shift = tonic_place(task.to_key.value) - tonic_place(key)
    if output.letter_steps != (4 * shift) % 7 or output.semitones != (7 * shift) % 12:
        return result(False, "letter_steps or semitones is not the interval between the tonics")
    if output.chords != sum(len(bar) for bar in bars):
        return result(False, "chords does not count the chart's chords")
    return result(True, "the chart is the seed's")


def verify_key_output(given, output):
    key = given.key.value
    expected = [name(tonic_place(key) + offset) for offset in DEGREES[mode_of(key)]]
    signature = sum(note.count("#") - note.count("b") for note in expected)
    if output.scale != expected or output.signature != signature or output.mode.value != mode_of(key):
        return result(False, f"the scale of {key} is {' '.join(expected)} with signature {signature}")
    return result(True, "the key is described correctly")


def verify_pin_output(task, output):
    key, bars, moved = answer(task)
    if output.source_key.value != key or [bar.chords for bar in output.source_bars] != bars:
        return result(False, "the pinned chart is not the seed's")
    if output.chart_sha256 != canonical_sha256({"source_key": key, "bars": bars}):
        return result(False, "the pinned chart's sha256 is wrong")
    if [bar.chords for bar in output.bars] != moved:
        return result(False, "the pinned transposition disagrees with the verifier's own")
    return result(True, "the answer key is the chart's transposition", chords=sum(len(bar) for bar in bars))


def verify_task(arguments, output, reference, workspace):
    if reference is None or verify_pin_output(arguments, reference)["valid"] is not True:
        return result(False, "the pinned answer key does not match the chart the seed gives")
    key, _, moved = answer(arguments)
    expected_total = sum(len(bar) for bar in moved)
    submitted = [bar.chords for bar in output.bars]
    submitted_total = sum(len(bar) for bar in submitted)
    wrong, correct = [], 0
    for b, bar in enumerate(moved):
        given = submitted[b] if b < len(submitted) else []
        for c, chord in enumerate(bar):
            got = given[c] if c < len(given) else None
            if got == chord:
                correct += 1
            else:
                wrong.append(f"bar {b + 1}, chord {c + 1}: {got if got is not None else 'missing'}, expected {chord}")
    problems = []
    if output.to_key is not arguments.to_key:
        problems.append(f"to_key is {output.to_key.value}, not the task's {arguments.to_key.value}")
    if len(submitted) != len(moved):
        problems.append(f"{len(submitted)} bars, expected {len(moved)}")
    extra = [b + 1 for b, bar in enumerate(submitted) if len(bar) != (len(moved[b]) if b < len(moved) else 0)]
    if extra:
        problems.append("wrong number of chords in bar(s) " + ", ".join(str(b) for b in extra[:8]))
    if wrong:
        problems.append(f"{len(wrong)} chord(s) wrong: " + "; ".join(wrong[:4]) + (" ..." if len(wrong) > 4 else ""))
    details = {
        "source_key": key,
        "to_key": arguments.to_key.value,
        "chords_expected": expected_total,
        "chords_submitted": submitted_total,
        "chords_correct": correct,
        "wrong": wrong,
    }
    score = correct / max(expected_total, submitted_total, 1)
    if problems:
        return result(False, "; ".join(problems), score=score, **details)
    return result(True, f"all {expected_total} chords are transposed from {key} to {arguments.to_key.value} correctly", **details)
