# Chord Chart Transpose

A `nanoagent.plugin/v0001` plugin. Its task, `transpose-chart`, gives an agent
a chord chart (8 to 16 bars, in one of the 30 major and minor keys) and a
target key of the same mode, and asks for the chart transposed, every root and
bass note spelled the way the target key spells it. The chart comes from a
seed, so every task can be rebuilt exactly, and a deterministic verifier
transposes it again with its own method and checks every chord symbol.

## Tools

| Tool | Does | Code |
|---|---|---|
| `get_chart` | The task's chart: its key, the target key, the interval between their tonics (`letter_steps`, `semitones`), the chord count and the bars | `src/plugin/chart.py` |
| `key_info` | A key's mode, its seven scale notes from the tonic and its signature (sharps, or minus the flats) | `src/plugin/chart.py` |
| `pin_transposition` | The answer key: the chart, its sha256 and its correct transposition | `src/plugin/chart.py` |

### Tasks

| Task | Does | Runner |
|---|---|---|
| `transpose-chart` | Transposes the chart into the target key and submits it bar by bar | `agent`, with `get_chart` and `key_info`; reference `pin_transposition` |

## The task

Input: `seed` (0 to 1,000,000,000) and `to_key`, one of `C G D A E B F# C#
F Bb Eb Ab Db Gb Cb` or `Am Em Bm F#m C#m G#m D#m A#m Dm Gm Cm Fm Bbm Ebm
Abm`. The seed picks the chart's key among the keys of `to_key`'s mode (it may
be `to_key` itself) and its chords: diatonic chords, secondary dominants,
borrowed chords (bVII, bVI, iv in major; V7, IV, the Neapolitan bII in minor),
augmented chords, inversions (`D/F#`) and chromatic basses (`C/Bb`), with
suffixes such as `m7`, `maj7#11`, `m7b5`, `7b9`, `13`, `sus4` and `add9`.

The agent calls `get_chart`, optionally `key_info`, then `submit` with
`to_key` and the bars, the same shape as the chart.

The rule: every note moves `letter_steps` letters and `semitones` semitones up,
the interval between the two tonics; its accidental is whatever makes the
pitch right. A note that would need a double sharp is written one letter up
(`F##` is `G`), one that would need a double flat one letter down (`Bbb` is
`A`). The suffix (`7b9`, `maj7#11`, ...) never changes.

## Ground truth and verification

The chart's harmony is drawn abstractly (scale degrees, alterations, suffixes,
bass notes) by a sha256-based generator (`src/plugin/rng.py`,
`src/plugin/progression.py`), never `random`, so a seed gives the same chart on
every machine. The tools spell notes as a letter plus a pitch from 0 to 11.

`verify_task` (in `verifier/fifths.py`):

1. Rebuilds the chart from the seed with its own copies of the generator, but
   spells it on the line of fifths (F -1, C 0, G 1, ... B 5; a sharp adds 7, a
   flat takes 7), and checks that the pinned answer key holds that chart (by
   sha256) and its transposition.
2. Transposes the chart by adding the distance between the tonics on the line
   of fifths, respelling any note beyond `B#` or `Fb` by 12 places: an
   independent method that must agree with the tools' letter arithmetic (it
   does on 2,000 seeds in the tests).
3. Compares every chord by bar and position, and names each one wrong,
   missing or extra, the bar count, and a wrong `to_key`.

The verdict is valid only when every chord is exactly right; its score is the
share of chords that are right.

## Layout

```text
.
├── nanoagent.yaml   # manifest: id, runtime, permissions (no network), tools, task
├── contract.py      # each tool's and task's typed input and output
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # environment variable names needed (none)
├── src/plugin/      # the MCP server (__main__.py), the generator (rng.py, progression.py) and the tools (chart.py)
├── tests/           # the verifier's tests, tool tests with hand-checked chords, a 2,000-chart agreement
│                    #   test, an MCP smoke test, and a scripted no-model agent (scripted_agent.py)
├── ui/              # renderers.js and renderers.css: outputs drawn from their JSON Schema
├── product/         # the product page: product.yaml and icon.svg
└── verifier/        # the deterministic verifier: fifths.py, its generator copies rng.py and progression.py, checks.py
```

## Develop and run

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
```

No network and no data files: every chart comes from its seed. NanoAgent
passes the folder the plugin may write to as `NANOAGENT_WORKSPACE`; this
plugin's tools write nothing there.
