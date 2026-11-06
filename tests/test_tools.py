"""The tools, the independent oracle, and the MCP server."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import anyio
import pytest
from helpers import task
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from scripted_agent import submission
from slimconfig import build_output, plain_output

from contract import Key, KeyInput
from plugin import get_chart, key_info, pin_transposition
from plugin.chart import chart, interval, move, transpose_chord
from verifier.fifths import answer, rebuild

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("note", "letters", "semitones", "expected"),
    [
        ("C", 2, 3, "Eb"),  # C to Eb: a minor third
        ("F#", 2, 3, "A"),
        ("B", 2, 3, "D"),
        ("Bb", 3, 5, "Eb"),  # a perfect fourth
        ("E", 0, 1, "E#"),
        ("Bb", 0, 2, "B#"),  # Bb up two semitones on the same letter: B#
        ("A", 0, 2, "B"),  # A## is respelled B
        ("F", 0, 2, "G"),  # F## is respelled G
        ("E", 0, 2, "F#"),  # E## is respelled F#
        ("C", 0, 10, "Bb"),  # Cbb is respelled Bb
        ("F", 0, 10, "Eb"),  # Fbb is respelled Eb
        ("G", 0, 0, "G"),
    ],
)
def test_notes_move_by_letters_and_semitones(note: str, letters: int, semitones: int, expected: str) -> None:
    assert move(note, letters, semitones) == expected


@pytest.mark.parametrize(
    ("symbol", "letters", "semitones", "expected"),
    [
        ("D/F#", 2, 3, "F/A"),  # C major to Eb major
        ("Cmaj7#11", 2, 3, "Ebmaj7#11"),
        ("Bm7b5", 2, 3, "Dm7b5"),
        ("G7b9/B", 6, 10, "F7b9/A"),  # C to Bb: down a whole step
        ("F#m7", 1, 1, "Gm7"),  # F# to G
        ("Gb", 6, 11, "F"),  # Gb major to F major
        ("C7sus4", 0, 0, "C7sus4"),
    ],
)
def test_hand_checked_chords(symbol: str, letters: int, semitones: int, expected: str) -> None:
    assert transpose_chord(symbol, letters, semitones) == expected


def test_malformed_symbols_are_refused() -> None:
    for junk in ("H7", "", "C/", "cm"):
        with pytest.raises(ValueError):
            transpose_chord(junk, 1, 2)


def test_key_info_gives_scales_and_signatures(tmp_path: Path) -> None:
    def info(key: str):
        return key_info(build_output({"key": key}, KeyInput), tmp_path)

    assert info("D").scale == ["D", "E", "F#", "G", "A", "B", "C#"] and info("D").signature == 2
    assert info("Cb").signature == -7 and info("C#").signature == 7
    assert info("Gm").scale == ["G", "A", "Bb", "C", "D", "Eb", "F"] and info("Gm").signature == -2
    assert info("A#m").signature == 7 and info("Abm").signature == -7
    for key in Key:
        assert len({note[0] for note in info(key.value).scale}) == 7


def test_intervals_between_keys() -> None:
    assert interval("C", "Eb") == (2, 3)
    assert interval("F#", "Gb") == (1, 0)
    assert interval("Eb", "C") == (5, 9)
    assert interval("Am", "Am") == (0, 0)


def test_the_source_key_has_the_target_keys_mode() -> None:
    for seed in range(200):
        for key in Key:
            assert chart(task(seed=seed, to_key=key.value))[0].endswith("m") == key.value.endswith("m")


def test_charts_have_8_to_16_bars_of_1_or_2_chords() -> None:
    for seed in range(300):
        _, bars = chart(task(seed=seed))
        assert 8 <= len(bars) <= 16 and all(1 <= len(bar) <= 2 for bar in bars)


def test_the_tools_and_the_verifier_agree_on_2000_charts(tmp_path: Path) -> None:
    keys = [key.value for key in Key]
    for seed in range(2000):
        given = task(seed=seed, to_key=keys[seed % len(keys)])
        source, bars = chart(given)
        assert (source, bars) == rebuild(given)
        pinned = pin_transposition(given, tmp_path)
        assert [bar.chords for bar in pinned.bars] == answer(given)[2], seed
        # The scripted agent, working from get_chart alone, agrees too.
        assert submission(plain_output(get_chart(given, tmp_path)))["bars"] == plain_output(pinned)["bars"]


def test_the_mcp_server_lists_and_runs_every_tool(tmp_path: Path) -> None:
    async def run() -> None:
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "plugin"], cwd=str(ROOT), env={**os.environ, "NANOAGENT_WORKSPACE": str(tmp_path)}
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            names = {tool.name for tool in (await session.list_tools()).tools}
            assert names == {"get_chart", "key_info", "pin_transposition"}
            given = {"seed": 1, "to_key": "Bbm"}
            got = await session.call_tool("get_chart", given)
            assert not got.isError and got.structuredContent["bars"]
            info = await session.call_tool("key_info", {"key": "F#"})
            assert not info.isError and info.structuredContent["signature"] == 6
            pinned = await session.call_tool("pin_transposition", given)
            assert not pinned.isError and pinned.structuredContent["bars"]
            bad = await session.call_tool("get_chart", {"seed": 1, "to_key": "H"})
            assert bad.isError

    anyio.run(run)
