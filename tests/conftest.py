"""Test fixtures: the Agg backend and a small deterministic instance."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402

REPO = __import__("pathlib").Path(__file__).resolve().parents[1]

#: A 6x6 grid with a wall, and an A*-shaped search over it. Small enough to
#: read in a failure message, big enough that every mark appears.
GRID = [
    [0, 0, 0, 0, 0, 0],
    [0, 1, 1, 1, 0, 0],
    [0, 0, 0, 1, 0, 0],
    [1, 1, 0, 1, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 1, 1, 1, 0],
]
EXPANDED = [(0, 0), (0, 1), (1, 0), (0, 2), (2, 0), (2, 1), (2, 2), (3, 2), (4, 2)]
FRONTIER = [(0, 3), (4, 1), (4, 3)]
PATH = [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2), (3, 2), (4, 2), (4, 3), (4, 4)]
PATHS = {
    "alpha": [(0, 0), (0, 1), (0, 2), (0, 2), (0, 3), (0, 4)],
    "beta": [(5, 5), (4, 5), (4, 4), (4, 3), (4, 2)],
    "gamma": [(0, 5), (0, 4), (1, 4), (2, 4), (3, 4)],
}
TREE = [
    (0, -1, 0, 6.0),
    (1, 0, 1, 5.0),
    (2, 0, 1, 5.5),
    (3, 1, 2, 4.0),
    (4, 1, 2, 4.5),
    (5, 3, 3, 3.0),
]
SERIES = {
    "reference": {4: [0.1, 0.12], 8: [0.4, 0.55], 16: [1.9, 2.4]},
    "candidate": {4: [0.05, 0.06], 8: [0.11, 0.13], 16: [0.3, 0.4]},
}
PHASES = {
    "64": {"kernel": 0.4, "h2d": 0.1, "d2h": 0.1, "host": 0.2},
    "128": {"kernel": 1.1, "h2d": 0.2, "d2h": 0.2, "host": 0.3},
}


@pytest.fixture(autouse=True)
def _close_figures():
    """Close every figure a test opened, so a long suite does not leak memory."""
    yield
    plt.close("all")


@pytest.fixture(autouse=True)
def _pristine_rcparams():
    """Fail loudly if a test (or the library) leaks rcParams into the session."""
    before = dict(plt.rcParams)
    yield
    after = dict(plt.rcParams)
    changed = {
        key for key in before if repr(before[key]) != repr(after.get(key))
    }
    plt.rcParams.update(before)
    assert not changed, f"rcParams leaked: {sorted(changed)}"


@pytest.fixture(params=[False, True], ids=["light", "dark"])
def dark(request) -> bool:
    """Run the test once in each scheme."""
    return request.param
