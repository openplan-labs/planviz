"""Internal helpers shared by every figure module.

Nothing here is public API. The two jobs it does are worth stating, because
they are the reason figures from different modules read as one system:

* **Axis furniture.** ``axes()`` and ``finish()`` apply the brand's chart rules
  — hairline spines in ``line``, tick labels in ``muted``, y-grid only, no top
  or right spine, titles in ``heading``.
* **Colour permanence.** Colours are stamped onto the artists rather than left
  to rcParams, so a figure returned from a :func:`planviz.style_context` block
  still looks right after the context closes and the caller saves it.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np

from .tokens import Tokens


def axes(
    ax,
    tokens: Tokens,
    figsize: tuple[float, float] | None = None,
    *,
    polar: bool = False,
):
    """Return ``(figure, ax)``, creating the axes when ``ax`` is ``None``."""
    import matplotlib.pyplot as plt

    if ax is None:
        figure = plt.figure(figsize=figsize or (6.4, 4.2))
        ax = figure.add_subplot(111, polar=polar)
    figure = ax.figure
    figure.set_facecolor(tokens.bg)
    figure.patch.set_alpha(1.0)
    ax.set_facecolor(tokens.bg_raised)
    return figure, ax


def style_axes(ax, tokens: Tokens, *, grid_axis: str | None = "y") -> None:
    """Apply the brand's axis rules to ``ax``: hairlines, muted ticks, y-grid."""
    ax.set_facecolor(tokens.bg_raised)
    for side in ("top", "right"):
        if side in ax.spines:
            ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        if side in ax.spines:
            ax.spines[side].set_color(tokens.line)
            ax.spines[side].set_linewidth(1.0)
    ax.tick_params(colors=tokens.muted, labelsize=9, which="both")
    for label in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
        label.set_color(tokens.muted)
    if grid_axis:
        ax.grid(True, axis=grid_axis, color=tokens.line, linewidth=0.6, alpha=0.9)
        ax.set_axisbelow(True)
    else:
        ax.grid(False)


def finish(
    ax,
    tokens: Tokens,
    *,
    title: str | None = None,
    xlabel: str | None = None,
    ylabel: str | None = None,
    grid_axis: str | None = "y",
):
    """Apply axis styling and the optional title/labels; return ``ax``."""
    style_axes(ax, tokens, grid_axis=grid_axis)
    if title:
        ax.set_title(title, color=tokens.heading, fontweight="semibold", pad=10)
    if xlabel is not None:
        ax.set_xlabel(xlabel, color=tokens.body, fontsize=10)
    if ylabel is not None:
        ax.set_ylabel(ylabel, color=tokens.body, fontsize=10)
    return ax


def legend(ax, tokens: Tokens, **kwargs):
    """Draw a frameless legend in body ink, or nothing if there are no labels."""
    handles, labels = ax.get_legend_handles_labels()
    if not handles:
        return None
    kwargs.setdefault("fontsize", 9)
    return ax.legend(
        handles, labels, frameon=False, labelcolor=tokens.body, **kwargs
    )


def caption(ax, tokens: Tokens, text: str, *, y: float = -0.16) -> None:
    """Write a muted caption under the axes — conditions, units, or a warning."""
    ax.annotate(
        text,
        xy=(0, y),
        xycoords="axes fraction",
        fontsize=8.5,
        color=tokens.muted,
        annotation_clip=False,
    )


def occupancy(grid: Any) -> np.ndarray:
    """Coerce ``grid`` to a boolean occupancy array — ``True`` means blocked.

    Accepts anything ``numpy`` can read as a 2-D array of numbers or booleans,
    indexed ``[row][col]`` with row 0 at the top.
    """
    array = np.asarray(grid)
    if array.ndim != 2:
        raise ValueError(
            f"grid must be 2-D indexed [row][col], got shape {array.shape}"
        )
    return array.astype(bool)


def as_paths(paths: Any) -> dict[str, list[tuple[float, float]]]:
    """Coerce ``paths`` to ``{name: [(row, col), ...]}`` preserving order.

    A mapping keeps its keys as agent names; a bare sequence of paths is named
    by index, which is what makes colour assignment stable across re-renders.
    """
    if hasattr(paths, "items"):
        items = list(paths.items())
    else:
        items = [(str(i), path) for i, path in enumerate(paths)]
    out = {}
    for name, path in items:
        cells = [(float(cell[0]), float(cell[1])) for cell in path]
        if not cells:
            raise ValueError(f"path {name!r} is empty")
        out[str(name)] = cells
    return out


def rails(count: int, index: int, width: float = 0.13) -> float:
    """Return the lateral offset for path ``index`` of ``count``.

    Agents share cells over time, so their routes are drawn on slightly offset
    rails; without this a four-agent corridor is a single line that says
    nothing about who is in it.
    """
    if count <= 1:
        return 0.0
    return width * (index - (count - 1) / 2) / max(1.0, count / 2)


def limits(values: Iterable[float], pad: float = 0.05) -> tuple[float, float]:
    """Return padded ``(low, high)`` limits for ``values``."""
    data = [v for v in values if v == v]
    if not data:
        return (0.0, 1.0)
    low, high = min(data), max(data)
    if low == high:
        return (low - 1, high + 1)
    span = (high - low) * pad
    return (low - span, high + span)


def series_colors(
    names: Sequence[str], tokens: Tokens, highlight: str | None = None
) -> dict[str, str]:
    """Assign colours to named series by stable index.

    The brand's rule for comparisons: the series being argued for takes
    ``path``, and every other series takes the agent ramp — never a second
    warm colour, and never one of the reserved semantic values.
    """
    colors = {name: tokens.agent(i) for i, name in enumerate(names)}
    if highlight is not None:
        if highlight not in colors:
            raise ValueError(
                f"highlight {highlight!r} is not one of {sorted(colors)}"
            )
        colors[highlight] = tokens.path
    return colors


def save(figure_or_ax, path, dpi: int = 200):
    """Save a figure (or the figure owning an axes) and return the path.

    Figure functions never save on their own — this is the explicit call.

        >>> import matplotlib; matplotlib.use("Agg")
        >>> import planviz, tempfile, os
        >>> ax = planviz.draw_grid([[0, 1], [0, 0]])
        >>> out = planviz.save(ax, os.path.join(tempfile.mkdtemp(), "grid.png"))
        >>> os.path.getsize(out) > 0
        True
    """
    from pathlib import Path

    figure = getattr(figure_or_ax, "figure", figure_or_ax)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(
        target,
        dpi=dpi,
        bbox_inches="tight",
        facecolor=figure.get_facecolor(),
    )
    return target
