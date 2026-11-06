"""The verifier on correct, wrong, missing, malformed and boundary results."""

from __future__ import annotations

from pathlib import Path

import pytest
from helpers import as_sandbox, gold_run, task
from slimconfig import plain_output

import verifier
from contract import ChartInput, KeyInput, TransposeOutput
from plugin import get_chart, key_info, pin_transposition
from plugin.chart import chart

TASK = "transpose-chart"


def find(predicate, to_keys=("C", "Eb", "F#", "Cb", "Am", "Ebm")) -> ChartInput:
    """The first task (seed 0 up) whose chart satisfies ``predicate(source_key, bars)``."""
    for seed in range(5000):
        for to_key in to_keys:
            given = task(seed=seed, to_key=to_key)
            if predicate(given, *chart(given)):
                return given
    raise AssertionError("no seed has that chart")


def submit(given: ChartInput, bars: list[list[str]], tmp_path: Path, to_key: str | None = None) -> dict:
    _, reference = gold_run(given, tmp_path)
    output = as_sandbox(
        {"to_key": to_key or given.to_key.value, "bars": [{"chords": bar} for bar in bars]}, TransposeOutput
    )
    return verifier.verify_task(TASK, given, output, reference, str(tmp_path))


def gold_bars(given: ChartInput, tmp_path: Path) -> list[list[str]]:
    output, _ = gold_run(given, tmp_path)
    return [list(bar.chords) for bar in output.bars]


def test_accepts_a_correct_transposition(tmp_path: Path) -> None:
    given = task()
    output, reference = gold_run(given, tmp_path)
    verdict = verifier.verify_task(TASK, given, output, reference, str(tmp_path))
    assert verdict["valid"] is True and verdict["score"] == 1.0, verdict["message"]


def test_rejects_an_enharmonic_misspelling(tmp_path: Path) -> None:
    # In Eb major, the note a semitone above A is Bb, never A#.
    given = task(seed=7, to_key="Eb")
    bars = gold_bars(given, tmp_path)
    b, c = next((b, c) for b, bar in enumerate(bars) for c, chord in enumerate(bar) if chord.startswith("Bb"))
    bars[b][c] = "A#" + bars[b][c][2:]
    verdict = submit(given, bars, tmp_path)
    assert verdict["valid"] is False and len(verdict["details"]["wrong"]) == 1
    assert 0 < verdict["score"] < 1


def test_rejects_a_changed_chord_quality(tmp_path: Path) -> None:
    given = task()
    bars = gold_bars(given, tmp_path)
    bars[0][0] = bars[0][0] + "7" if not bars[0][0].endswith("7") else bars[0][0][:-1]
    assert submit(given, bars, tmp_path)["valid"] is False


def test_rejects_a_missing_chord_and_a_missing_bar(tmp_path: Path) -> None:
    given = task()
    bars = gold_bars(given, tmp_path)
    one_short = [bar[:] for bar in bars]
    one_short[-1] = one_short[-1][:-1]
    verdict = submit(given, one_short, tmp_path)
    assert verdict["valid"] is False and any("missing" in w for w in verdict["details"]["wrong"])
    verdict = submit(given, bars[:-1], tmp_path)
    assert verdict["valid"] is False and "bars, expected" in verdict["message"]


def test_rejects_extra_chords(tmp_path: Path) -> None:
    given = task()
    bars = gold_bars(given, tmp_path)
    verdict = submit(given, bars + [["C"]], tmp_path)
    assert verdict["valid"] is False and verdict["score"] < 1


def test_rejects_an_empty_chart(tmp_path: Path) -> None:
    given = task()
    verdict = submit(given, [], tmp_path)
    assert verdict["valid"] is False and verdict["score"] == 0.0


def test_rejects_the_wrong_target_key(tmp_path: Path) -> None:
    given = task(to_key="Eb")
    verdict = submit(given, gold_bars(given, tmp_path), tmp_path, to_key="D#m")
    assert verdict["valid"] is False and "to_key" in verdict["message"]


def test_rejects_malformed_chord_symbols(tmp_path: Path) -> None:
    given = task()
    bars = gold_bars(given, tmp_path)
    for junk in ("", "H7", "eb", "Ebmaj7/", "Eb m"):
        broken = [bar[:] for bar in bars]
        broken[0][0] = junk
        assert submit(given, broken, tmp_path)["valid"] is False


def test_rejects_an_untransposed_chart(tmp_path: Path) -> None:
    given = find(lambda g, key, bars: key != g.to_key.value)
    _, bars = chart(given)
    assert submit(given, bars, tmp_path)["valid"] is False


def test_rejects_a_tampered_answer_key(tmp_path: Path) -> None:
    given = task()
    output, reference = gold_run(given, tmp_path)
    reference.bars = reference.bars[1:]
    assert verifier.verify_task(TASK, given, output, reference, str(tmp_path))["valid"] is False
    output, reference = gold_run(given, tmp_path)
    reference.chart_sha256 = "0" * 64
    assert verifier.verify_task(TASK, given, output, reference, str(tmp_path))["valid"] is False


def test_identity_transposition_leaves_the_chart_unchanged(tmp_path: Path) -> None:
    given = find(lambda g, key, bars: key == g.to_key.value)
    output, reference = gold_run(given, tmp_path)
    assert [list(bar.chords) for bar in output.bars] == chart(given)[1]
    assert verifier.verify_task(TASK, given, output, reference, str(tmp_path))["valid"] is True


def test_f_sharp_to_g_flat_changes_every_letter(tmp_path: Path) -> None:
    given = find(lambda g, key, bars: key == "F#", to_keys=("Gb",))
    output, reference = gold_run(given, tmp_path)
    source = [chord for bar in chart(given)[1] for chord in bar]
    moved = [chord for bar in output.bars for chord in bar.chords]
    assert all(a[0] != b[0] for a, b in zip(source, moved))
    assert verifier.verify_task(TASK, given, output, reference, str(tmp_path))["valid"] is True
    # Keeping F# spellings in Gb (enharmonically the same pitches) is wrong.
    assert submit(given, chart(given)[1], tmp_path)["valid"] is False


def test_into_c_flat_major(tmp_path: Path) -> None:
    given = task(seed=2, to_key="Cb")
    output, reference = gold_run(given, tmp_path)
    assert verifier.verify_task(TASK, given, output, reference, str(tmp_path))["valid"] is True
    assert any(chord.startswith("Cb") for bar in output.bars for chord in bar.chords)


def test_double_accidentals_are_respelled(tmp_path: Path) -> None:
    # Cb major to C# major moves every letter-name two semitones: Bbb (written A in Cb) becomes B, not A##.
    def needs_respelling(g, key, bars):
        return key == "Cb" and any(chord[0] == "A" and chord[1:2] not in ("#", "b") for bar in bars for chord in bar)

    given = find(needs_respelling, to_keys=("C#",))
    output, reference = gold_run(given, tmp_path)
    moved = [chord for bar in output.bars for chord in bar.chords]
    assert not any("##" in chord or "bb" in chord for chord in moved)
    assert verifier.verify_task(TASK, given, output, reference, str(tmp_path))["valid"] is True


def test_slash_chords_move_their_bass(tmp_path: Path) -> None:
    given = find(lambda g, key, bars: key != g.to_key.value and any("/" in chord for bar in bars for chord in bar))
    bars = gold_bars(given, tmp_path)
    b, c = next((b, c) for b, bar in enumerate(bars) for c, chord in enumerate(bar) if "/" in chord)
    source_bass = chart(given)[1][b][c].split("/")[1]
    assert submit(given, bars, tmp_path)["valid"] is True
    bars[b][c] = bars[b][c].split("/")[0] + "/" + source_bass  # the bass left untransposed
    assert submit(given, bars, tmp_path)["valid"] is False


@pytest.mark.parametrize("to_key", ["C", "G", "F#", "C#", "F", "Gb", "Cb", "Am", "D#m", "A#m", "Abm", "Bbm"])
@pytest.mark.parametrize("seed", range(8))
def test_gold_runs_pass_for_every_kind_of_key(tmp_path: Path, seed: int, to_key: str) -> None:
    given = task(seed=seed, to_key=to_key)
    output, reference = gold_run(given, tmp_path)
    verdict = verifier.verify_task(TASK, given, output, reference, str(tmp_path))
    assert verdict["valid"] is True, verdict["message"]


def test_input_checks_refuse_a_bad_seed() -> None:
    assert verifier.verify_input("get_chart", task(seed=-1))["valid"] is False
    assert verifier.verify_input("get_chart", task(seed=10**9 + 1))["valid"] is False
    assert verifier.verify_input("get_chart", task(seed=10**9))["valid"] is True


def test_tool_outputs_are_checked(tmp_path: Path) -> None:
    given = task()
    made = as_sandbox(get_chart(given, tmp_path), type(get_chart(given, tmp_path)))
    assert verifier.verify_output("get_chart", given, made, str(tmp_path))["valid"] is True
    made.semitones = (made.semitones + 1) % 12
    assert verifier.verify_output("get_chart", given, made, str(tmp_path))["valid"] is False

    key = as_sandbox({"key": "Ebm"}, KeyInput)
    info = as_sandbox(plain_output(key_info(key, tmp_path)), type(key_info(key, tmp_path)))
    assert verifier.verify_output("key_info", key, info, str(tmp_path))["valid"] is True
    info.signature = -5
    assert verifier.verify_output("key_info", key, info, str(tmp_path))["valid"] is False

    pinned = as_sandbox(pin_transposition(given, tmp_path), type(pin_transposition(given, tmp_path)))
    assert verifier.verify_output("pin_transposition", given, pinned, str(tmp_path))["valid"] is True
