"""The vendored brand values, and the two ways they can go wrong.

Vendoring buys offline determinism at the cost of drift. Two checks guard it:

* **Internal drift** — ``planviz/tokens.py`` and
  ``planviz/styles/frontier.mplstyle`` are two copies of the same palette, and
  they are cross-checked here with no network involved.
* **External drift** — whether either still matches ``openplan-labs/branding``.
  That needs the network, so it skips locally and runs as its own CI job
  (``python scripts/sync_tokens.py --check``), where a failure is the point.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from urllib.error import URLError

import matplotlib.colors as mcolors
import pytest

import planviz
from planviz import tokens

REPO = Path(__file__).resolve().parents[1]
BRANDING = REPO.parent / "branding"


def _sync_module():
    spec = importlib.util.spec_from_file_location(
        "sync_tokens", REPO / "scripts" / "sync_tokens.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["sync_tokens"] = module
    spec.loader.exec_module(module)
    return module


def test_both_schemes_are_complete():
    for scheme in (tokens.LIGHT, tokens.DARK):
        for field in (
            "bg", "bg_raised", "line", "heading", "body", "muted", "faint",
            "path", "path_soft", "frontier", "expanded",
        ):
            value = getattr(scheme, field)
            assert value, f"{scheme.mode}.{field} is empty"
            mcolors.to_rgba(value)  # raises if matplotlib cannot read it


def test_the_agent_ramp_is_eight_wide_and_shared():
    assert len(tokens.AGENT_RAMP) == 8
    assert tokens.LIGHT.agents == tokens.DARK.agents == tokens.AGENT_RAMP


def test_agent_identity_is_stable_and_falls_back_to_shape():
    assert tokens.LIGHT.agent(0) == tokens.AGENT_RAMP[0]
    assert tokens.LIGHT.agent(8) == tokens.AGENT_RAMP[0]
    assert tokens.LIGHT.marker(0) != tokens.LIGHT.marker(8)
    names = ["gamma", "alpha", "beta"]
    assert tokens.LIGHT.agent_colors(names)["gamma"] == tokens.AGENT_RAMP[0]


def test_path_is_the_only_warm_value():
    """Hue check: ``path`` sits in the warm arc; nothing else does."""
    warm = {}
    for scheme in (tokens.LIGHT, tokens.DARK):
        for field in ("path", "frontier", "expanded", "faint", "muted", "body"):
            hue = mcolors.rgb_to_hsv(mcolors.to_rgb(getattr(scheme, field)))[0]
            warm[f"{scheme.mode}.{field}"] = hue < 0.12 or hue > 0.95
    assert [key for key, is_warm in warm.items() if is_warm] == [
        "light.path",
        "dark.path",
    ]


def test_the_sequential_ramp_runs_cool_to_warm():
    cmap = tokens.LIGHT.sequential()
    assert cmap.N == 256
    assert mcolors.to_hex(cmap(0.0)) == tokens.LIGHT.expanded
    assert mcolors.to_hex(cmap(1.0)) == tokens.LIGHT.path


def test_translucent_tokens_are_matplotlib_readable():
    """The brand publishes ``pathSoft`` as CSS ``rgba()``; we ship it as hex."""
    assert tokens.LIGHT.path_soft.startswith("#")
    assert len(tokens.LIGHT.path_soft) == 9
    assert mcolors.to_rgba(tokens.LIGHT.path_soft)[3] < 0.2


def test_the_stylesheet_and_the_token_module_agree():
    """The two vendored artifacts must not drift apart from each other."""
    import matplotlib.pyplot as plt

    # matplotlib accepts bare hex in a stylesheet and keeps it bare in
    # rcParams, so normalise before comparing.
    def hexed(value: str) -> str:
        return value if value.startswith("#") else f"#{value}"

    with plt.style.context(str(planviz.STYLE_PATH)):
        cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]
        face = plt.rcParams["axes.facecolor"]
        ground = plt.rcParams["figure.facecolor"]
        grid = plt.rcParams["grid.color"]
    assert [hexed(color) for color in cycle] == list(tokens.AGENT_RAMP)
    assert hexed(face) == tokens.LIGHT.bg_raised
    assert hexed(ground) == tokens.LIGHT.bg
    assert hexed(grid) == tokens.LIGHT.line


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(str(BRANDING), id="local-checkout"),
        pytest.param(None, id="branding-repo"),
    ],
)
def test_vendored_tokens_match_the_branding_repo(source):
    """Skips when the branding source is unreachable; CI runs it for real."""
    sync = _sync_module()
    argv = ["--check"] + (["--source", source] if source else [])
    if source and not Path(source).is_dir():
        pytest.skip(f"no branding checkout at {source}")
    try:
        assert sync.main(argv) == 0, "vendored tokens have drifted from branding"
    except (URLError, OSError) as error:  # offline runner
        pytest.skip(f"branding source unreachable: {error}")


def test_the_generator_is_idempotent():
    """Regenerating from the shipped values must reproduce the shipped file."""
    sync = _sync_module()
    spec = {
        "version": tokens.SPEC_VERSION,
        "agents": {"value": list(tokens.AGENT_RAMP)},
        "font": {key: {"value": value} for key, value in tokens.FONTS.items()},
    }
    for mode, scheme in (("light", tokens.LIGHT), ("dark", tokens.DARK)):
        spec[mode] = {
            key: {"value": getattr(scheme, field)}
            for field, key in sync._FIELDS
        }
    rendered = sync.render(spec)
    assert rendered == (REPO / "planviz" / "tokens.py").read_text()
