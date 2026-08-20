"""Grid maps, multi-agent routes, and the canonical search figure.

Three pictures, in the order a reader meets them:

* :func:`draw_grid` — the problem. Obstacles are structure, so they take
  ``line``, the same value as a table rule.
* :func:`draw_search` — what the search did. The three-mark legend
  (filled dot, hollow ring, connected stroke) is the brand's canonical figure
  and the one most worth copying.
* :func:`draw_paths` — what it returned, for many agents at once.

Grids are indexed ``[row][col]`` with row 0 at the top, and cells are drawn at
integer coordinates, so ``(0, 0)`` is the top-left cell centre. Nothing here
knows about ``pymapf``, ``cuplan`` or ``jupyddl`` types: a grid is any 2-D
array-like where truthy means blocked, and a path is any sequence of
``(row, col)`` pairs.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np

from . import _common
from .style import style_context
from .tokens import Tokens

__all__ = ["draw_grid", "draw_paths", "draw_search", "MARKS"]

#: The legend from ``branding/brand/figures.md``, as matplotlib keyword sets.
#: Radii there are in points; matplotlib's ``markersize`` is a diameter.
MARKS = {
    "unvisited": {"marker": "o", "markersize": 3.0, "linestyle": "none"},
    "expanded": {"marker": "o", "markersize": 5.0, "linestyle": "none"},
    "frontier": {
        "marker": "o",
        "markersize": 6.0,
        "markerfacecolor": "none",
        "markeredgewidth": 1.5,
        "linestyle": "none",
    },
    "path": {"linewidth": 2.5, "solid_capstyle": "round", "solid_joinstyle": "round"},
    "start": {
        "marker": "o",
        "markersize": 7.0,
        "markerfacecolor": "none",
        "markeredgewidth": 1.8,
        "linestyle": "none",
    },
    "goal": {"marker": "o", "markersize": 7.0, "linestyle": "none"},
}

#: Above this many agents, hue stops being an identity channel and the figure
#: switches to a single colour with opacity — the brand's multi-agent rule.
CROWD = 8


def _extent(shape: tuple[int, int]):
    height, width = shape
    return (-0.5, width - 0.5, height - 0.5, -0.5)


def _shape_of(grid, paths, shape) -> tuple[int, int]:
    if shape is not None:
        return (int(shape[0]), int(shape[1]))
    if grid is not None:
        return _common.occupancy(grid).shape  # type: ignore[return-value]
    cells = [cell for path in (paths or {}).values() for cell in path]
    if not cells:
        raise ValueError("pass a grid or a shape: nothing to size the axes from")
    return (
        int(max(cell[0] for cell in cells)) + 1,
        int(max(cell[1] for cell in cells)) + 1,
    )


def _figsize(shape: tuple[int, int], figsize):
    if figsize is not None:
        return figsize
    height, width = shape
    scale = 0.3 if max(shape) <= 24 else 6.4 / max(shape)
    return (
        float(np.clip(width * scale, 3.2, 9.0)),
        float(np.clip(height * scale, 3.2, 9.0)),
    )


def _map_axes(ax, tokens: Tokens, shape, figsize):
    figure, ax = _common.axes(ax, tokens, _figsize(shape, figsize))
    height, width = shape
    ax.set_xlim(-0.5, width - 0.5)
    ax.set_ylim(height - 0.5, -0.5)  # row 0 at the top
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color(tokens.line)
        spine.set_linewidth(1.0)
    return figure, ax


def _draw_obstacles(ax, grid, tokens: Tokens) -> None:
    from matplotlib.colors import ListedColormap

    mask = _common.occupancy(grid)
    ax.imshow(
        mask.astype(float),
        cmap=ListedColormap([tokens.bg_raised, tokens.line]),
        vmin=0,
        vmax=1,
        extent=_extent(mask.shape),
        interpolation="nearest",
        zorder=1,
    )


def _title(ax, tokens: Tokens, title: str | None) -> None:
    if title:
        ax.set_title(title, color=tokens.heading, fontweight="semibold", pad=10)


def _cells(points: Iterable | None) -> np.ndarray:
    """Return an ``(n, 2)`` array of ``(row, col)`` pairs, possibly empty."""
    if points is None:
        return np.empty((0, 2), dtype=float)
    array = np.asarray(list(points), dtype=float)
    if array.size == 0:
        return np.empty((0, 2), dtype=float)
    if array.ndim != 2 or array.shape[1] != 2:
        raise ValueError("expected a sequence of (row, col) pairs")
    return array


def draw_grid(
    grid: Any = None,
    *,
    shape: tuple[int, int] | None = None,
    ax=None,
    dark: bool = False,
    title: str | None = None,
    lattice: bool = False,
    figsize: tuple[float, float] | None = None,
):
    """Draw an occupancy grid: blocked cells filled, nothing else.

    No lattice is drawn by default. The cells *are* the grid, and a lattice
    under an occupancy map doubles the line count for no information — see
    ``brand/figures.md``. Pass ``lattice=True`` for a small teaching figure
    where the cell boundaries are the point.

    Args:
        grid: 2-D array-like indexed ``[row][col]``; truthy means blocked.
            May be omitted if ``shape`` is given.
        shape: ``(height, width)`` for an empty grid.
        ax: draw into this axes instead of creating one.
        dark: use the dark scheme.
        title: axes title.
        lattice: draw hairline cell boundaries.
        figsize: overrides the size derived from the grid's aspect.

    Returns:
        The :class:`~matplotlib.axes.Axes` drawn on.

    Example:
        >>> import matplotlib; matplotlib.use("Agg")
        >>> import planviz
        >>> ax = planviz.draw_grid([[0, 0, 1], [0, 1, 0], [0, 0, 0]])
        >>> tuple(float(v) for v in ax.get_xlim())
        (-0.5, 2.5)
    """
    with style_context(dark) as tokens:
        resolved = _shape_of(grid, None, shape)
        _, ax = _map_axes(ax, tokens, resolved, figsize)
        if grid is not None:
            _draw_obstacles(ax, grid, tokens)
        if lattice:
            height, width = resolved
            for col in range(width + 1):
                ax.axvline(col - 0.5, color=tokens.line, linewidth=0.6, zorder=0.5)
            for row in range(height + 1):
                ax.axhline(row - 0.5, color=tokens.line, linewidth=0.6, zorder=0.5)
        _title(ax, tokens, title)
    return ax


def draw_paths(
    paths: Any,
    grid: Any = None,
    *,
    shape: tuple[int, int] | None = None,
    ax=None,
    dark: bool = False,
    highlight: str | None = None,
    labels: bool = True,
    offsets: bool = True,
    endpoints: bool = True,
    title: str | None = None,
    figsize: tuple[float, float] | None = None,
):
    """Draw multi-agent routes over a grid — one stroke per agent.

    Colour comes from the agent ramp by **stable index**, so re-rendering with
    a different agent order does not reshuffle the figure. Three rules from
    ``brand/figures.md`` are enforced here:

    * past eight agents, individual hues stop being readable, so the figure
      switches to one colour at reduced opacity;
    * when ``highlight`` names an agent, that agent takes ``path`` — the
      solution accent — and every other agent drops to ``faint``;
    * each route starts on a hollow ring and ends on a filled disc, so
      direction is carried without arrowheads.

    Args:
        paths: ``{name: [(row, col), ...]}``, or a sequence of paths that will
            be named by index.
        grid: optional occupancy grid to draw underneath.
        shape: ``(height, width)`` when there is no grid.
        ax: draw into this axes instead of creating one.
        dark: use the dark scheme.
        highlight: name of the one agent this figure is about.
        labels: annotate each route with its agent name.
        offsets: draw routes on slightly offset rails so a shared corridor
            still shows how many agents are in it.
        endpoints: draw the start ring and goal disc.
        title: axes title.
        figsize: overrides the size derived from the grid's aspect.

    Returns:
        The :class:`~matplotlib.axes.Axes` drawn on.

    Example:
        >>> import matplotlib; matplotlib.use("Agg")
        >>> import planviz
        >>> ax = planviz.draw_paths(
        ...     {"a": [(0, 0), (0, 1), (1, 1)], "b": [(2, 0), (1, 0), (1, 1)]},
        ...     shape=(3, 3),
        ... )
        >>> len(ax.lines) > 0
        True
    """
    routes = _common.as_paths(paths)
    with style_context(dark) as tokens:
        resolved = _shape_of(grid, routes, shape)
        _, ax = _map_axes(ax, tokens, resolved, figsize)
        if grid is not None:
            _draw_obstacles(ax, grid, tokens)

        names = list(routes)
        crowded = len(names) > CROWD and highlight is None
        if highlight is not None:
            colors = {name: tokens.faint for name in names}
            colors[highlight] = tokens.path
        elif crowded:
            colors = {name: tokens.expanded for name in names}
        else:
            colors = _common.series_colors(names, tokens)
        alpha = 0.55 if crowded else 0.95

        for index, name in enumerate(names):
            path = routes[name]
            shift = _common.rails(len(names), index) if offsets else 0.0
            xs = [cell[1] + shift for cell in path]
            ys = [cell[0] + shift for cell in path]
            color = colors[name]
            top = 4 if (highlight is None or name == highlight) else 3
            if not crowded:
                # A wide panel-coloured underlay keeps crossing rails legible.
                ax.plot(
                    xs, ys, color=tokens.bg_raised, linewidth=4.5,
                    solid_capstyle="round", zorder=top - 0.5,
                )
            ax.plot(
                xs, ys, color=color, alpha=alpha, zorder=top,
                label=None if crowded else name, **MARKS["path"],
            )
            if endpoints and not crowded:
                ax.plot(
                    xs[0], ys[0], markeredgecolor=color, zorder=top + 1,
                    **MARKS["start"],
                )
                ax.plot(
                    xs[-1], ys[-1], color=color,
                    markeredgecolor=tokens.bg_raised, markeredgewidth=1.0,
                    zorder=top + 1, **MARKS["goal"],
                )
            if labels and not crowded:
                ax.annotate(
                    name,
                    (xs[0], ys[0]),
                    textcoords="offset points",
                    xytext=(0, 9),
                    ha="center",
                    fontsize=8,
                    color=tokens.muted,
                    zorder=6,
                )
        if crowded:
            _common.caption(
                ax,
                tokens,
                f"{len(names)} agents — drawn by density, not by colour",
                y=-0.04,
            )
        _title(ax, tokens, title)
    return ax


def draw_search(
    expanded: Iterable | None = None,
    frontier: Iterable | None = None,
    path: Sequence | None = None,
    *,
    grid: Any = None,
    shape: tuple[int, int] | None = None,
    start: tuple[int, int] | None = None,
    goal: tuple[int, int] | None = None,
    unvisited: bool = True,
    ax=None,
    dark: bool = False,
    legend: bool = True,
    title: str | None = None,
    figsize: tuple[float, float] | None = None,
):
    """Draw the three sets of a search: closed list, open list, and solution.

    This is the organisation's canonical figure. The three sets differ by
    **shape** as well as hue — small filled dot, hollow ring, connected stroke —
    which is the channel that survives greyscale printing and red/green colour
    blindness. The path is drawn last and is the only continuous element.

    One idea per figure: this draws the search *and* its result at full
    strength, which is right for a legend plate and for the final frame of an
    animation. For a figure about expansion order alone, pass ``path=None``.

    Args:
        expanded: cells in the closed list, as ``(row, col)`` pairs.
        frontier: cells in the open list.
        path: the returned solution, in order.
        grid: optional occupancy grid to draw underneath.
        shape: ``(height, width)`` when there is no grid.
        start: start cell — a hollow ring. Defaults to the path's first cell.
        goal: goal cell — a filled disc. Defaults to the path's last cell.
        unvisited: stipple the never-touched free cells in ``faint``.
        ax: draw into this axes instead of creating one.
        dark: use the dark scheme.
        legend: draw the three-mark legend. Worth keeping the first time a
            reader meets the figure; drop it once they know the mapping.
        title: axes title.
        figsize: overrides the size derived from the grid's aspect.

    Returns:
        The :class:`~matplotlib.axes.Axes` drawn on.

    Example:
        >>> import matplotlib; matplotlib.use("Agg")
        >>> import planviz
        >>> ax = planviz.draw_search(
        ...     expanded=[(0, 0), (0, 1), (1, 0)],
        ...     frontier=[(1, 1), (2, 0)],
        ...     path=[(0, 0), (1, 0), (2, 0)],
        ...     shape=(3, 3),
        ... )
        >>> ax.get_title()
        ''
    """
    closed = _cells(expanded)
    open_list = _cells(frontier)
    solution = _cells(path)

    with style_context(dark) as tokens:
        pool = {"grid": grid, "shape": shape}
        if shape is None and grid is None:
            stacked = np.vstack([closed, open_list, solution])
            if stacked.size == 0:
                raise ValueError("nothing to draw: pass a grid, a shape, or cells")
            pool["shape"] = (
                int(stacked[:, 0].max()) + 1,
                int(stacked[:, 1].max()) + 1,
            )
        resolved = _shape_of(pool["grid"], None, pool["shape"])
        _, ax = _map_axes(ax, tokens, resolved, figsize)
        if grid is not None:
            _draw_obstacles(ax, grid, tokens)

        if unvisited:
            height, width = resolved
            blocked = (
                _common.occupancy(grid)
                if grid is not None
                else np.zeros(resolved, dtype=bool)
            )
            touched = np.zeros(resolved, dtype=bool)
            for cells in (closed, open_list, solution):
                for row, col in cells.astype(int):
                    if 0 <= row < height and 0 <= col < width:
                        touched[row, col] = True
            rows, cols = np.nonzero(~blocked & ~touched)
            if rows.size:
                ax.plot(
                    cols, rows, color=tokens.faint, alpha=0.55, zorder=2,
                    label="unvisited" if legend else None, **MARKS["unvisited"],
                )

        if closed.size:
            ax.plot(
                closed[:, 1], closed[:, 0], color=tokens.expanded, zorder=3,
                label="expanded" if legend else None, **MARKS["expanded"],
            )
        if open_list.size:
            ax.plot(
                open_list[:, 1], open_list[:, 0], markeredgecolor=tokens.frontier,
                zorder=4, label="frontier" if legend else None, **MARKS["frontier"],
            )
        if solution.size:
            # Drawn last, and the only connected element in the figure.
            ax.plot(
                solution[:, 1], solution[:, 0], color=tokens.path, zorder=5,
                label="path" if legend else None, **MARKS["path"],
            )

        origin = start if start is not None else (
            tuple(solution[0]) if solution.size else None
        )
        target = goal if goal is not None else (
            tuple(solution[-1]) if solution.size else None
        )
        if origin is not None:
            ax.plot(
                origin[1], origin[0], markeredgecolor=tokens.path, zorder=6,
                label="start" if legend else None, **MARKS["start"],
            )
        if target is not None:
            ax.plot(
                target[1], target[0], color=tokens.path,
                markeredgecolor=tokens.bg_raised, markeredgewidth=1.0, zorder=6,
                label="goal" if legend else None, **MARKS["goal"],
            )

        if legend:
            handles, labels = ax.get_legend_handles_labels()
            if handles:
                ax.legend(
                    handles,
                    labels,
                    frameon=False,
                    labelcolor=tokens.body,
                    fontsize=8.5,
                    loc="upper left",
                    bbox_to_anchor=(0.0, -0.02),
                    ncol=min(len(handles), 3),
                    handletextpad=0.5,
                    columnspacing=1.4,
                )
        _title(ax, tokens, title)
    return ax
