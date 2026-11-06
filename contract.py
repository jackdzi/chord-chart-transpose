"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    GET_CHART = "get_chart"
    KEY_INFO = "key_info"
    PIN_TRANSPOSITION = "pin_transposition"


class Task(Enum):
    TRANSPOSE_CHART = "transpose-chart"


class Key(Enum):
    C = "C"
    G = "G"
    D = "D"
    A = "A"
    E = "E"
    B = "B"
    F_SHARP = "F#"
    C_SHARP = "C#"
    F = "F"
    B_FLAT = "Bb"
    E_FLAT = "Eb"
    A_FLAT = "Ab"
    D_FLAT = "Db"
    G_FLAT = "Gb"
    C_FLAT = "Cb"
    A_MINOR = "Am"
    E_MINOR = "Em"
    B_MINOR = "Bm"
    F_SHARP_MINOR = "F#m"
    C_SHARP_MINOR = "C#m"
    G_SHARP_MINOR = "G#m"
    D_SHARP_MINOR = "D#m"
    A_SHARP_MINOR = "A#m"
    D_MINOR = "Dm"
    G_MINOR = "Gm"
    C_MINOR = "Cm"
    F_MINOR = "Fm"
    B_FLAT_MINOR = "Bbm"
    E_FLAT_MINOR = "Ebm"
    A_FLAT_MINOR = "Abm"


class Mode(Enum):
    MAJOR = "major"
    MINOR = "minor"


KEY = "A key: its tonic, with a trailing m for a minor key, e.g. Bb, F#m"
TASK = "The task input, copied exactly as given"
BARS = "The chart's bars, in order"


@dataclass
class ChartInput(Output):
    seed: Annotated[int, "Which chart: any integer from 0 to 1000000000; the same seed always gives the same chart"]
    to_key: Annotated[Key, "The key to transpose into; the chart is in a key of the same mode (major or minor)"]


@dataclass
class Bar(Output):
    chords: Annotated[list[str], "The bar's chord symbols, in order, e.g. [\"Bbmaj7\", \"F/A\"]"]


@dataclass
class ChartOutput(Output):
    source_key: Annotated[Key, "The key the chart is written in"]
    to_key: Annotated[Key, "The key to transpose into"]
    letter_steps: Annotated[int, "How many letters up the target tonic is from the source tonic, 0 to 6 (C to E is 2)"]
    semitones: Annotated[int, "How many semitones up the target tonic is from the source tonic, 0 to 11"]
    chords: Annotated[int, "How many chord symbols the chart holds"]
    bars: Annotated[list[Bar], BARS]


@dataclass
class KeyInput(Output):
    key: Annotated[Key, KEY]


@dataclass
class KeyOutput(Output):
    key: Annotated[Key, KEY]
    mode: Annotated[Mode, "major or minor (natural minor)"]
    scale: Annotated[list[str], "The key's seven scale notes from the tonic up, e.g. [\"D\", \"E\", \"F#\", \"G\", \"A\", \"B\", \"C#\"]"]
    signature: Annotated[int, "The key signature: the number of sharps, or minus the number of flats"]


@dataclass
class TransposeOutput(Output):
    to_key: Annotated[Key, "The key transposed into, as the task gives it"]
    bars: Annotated[list[Bar], "The transposed chart: the same bars and chords per bar as the original, in order"]


@dataclass
class PinOutput(Output):
    chart_sha256: Annotated[str, "sha256 of the source key and source bars as canonical JSON"]
    source_key: Annotated[Key, "The key the chart is written in"]
    source_bars: Annotated[list[Bar], "The original chart's bars"]
    bars: Annotated[list[Bar], "The correctly transposed chart's bars"]


TOOLS = {
    Tool.GET_CHART: (ChartInput, ChartOutput),
    Tool.KEY_INFO: (KeyInput, KeyOutput),
    Tool.PIN_TRANSPOSITION: (ChartInput, PinOutput),
}
TASKS = {Task.TRANSPOSE_CHART: (ChartInput, TransposeOutput)}
