from __future__ import annotations

from pathlib import Path

from scripted_agent import submission
from slimconfig import build_output, plain_output

from contract import ChartInput, PinOutput, TransposeOutput
from plugin import get_chart, pin_transposition


def as_sandbox(value, cls):
    """A value as NanoAgent's verifier sandbox hands it over: rebuilt from its JSON."""
    return build_output(plain_output(value) if not isinstance(value, dict) else value, cls)


def task(seed: int = 7, to_key: str = "Eb") -> ChartInput:
    return build_output({"seed": seed, "to_key": to_key}, ChartInput)


def gold_run(given: ChartInput, workspace: Path) -> tuple[TransposeOutput, PinOutput]:
    """A correct run through the real tools: get_chart, then the submitted output."""
    chart = plain_output(get_chart(given, workspace))
    output = as_sandbox(submission(chart), TransposeOutput)
    reference = as_sandbox(pin_transposition(given, workspace), PinOutput)
    return output, reference
