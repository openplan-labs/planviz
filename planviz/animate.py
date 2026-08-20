"""Animations: agents executing a plan, and the search that produced it.

Both build a :class:`~matplotlib.animation.FuncAnimation` and neither writes a
file — use :func:`save_animation` for that, or :func:`to_jshtml` to embed one
in a notebook.

:func:`animate_search` follows the brand's one rule for search animations: the
frontier moves, the expanded set **accumulates**, and the path appears once at
the end and stays. The accumulated closed list is the cost of the search, so
fading it out hides the thing the figure is arguing about.

GIFs are capped at 12 fps and 800 px wide by :func:`save_animation`, because
they are read in a GitHub README on a train.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from . import _common
from .grids import CROWD, MARKS, _draw_obstacles, _map_axes, _shape_of, _title
from .style import style_context

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from matplotlib.animation import FuncAnimation

__all__ = [
    "animate_paths",
    "animate_search",
    "save_animation",
    "to_jshtml",
    "GIF_FPS",
    "GIF_WIDTH_PX",
]

#: The brand's cap for animated GIFs in a README.
GIF_FPS = 12
GIF_WIDTH_PX = 800

#: Interpolation frames per timestep. Six reads as motion at 12–20 fps without
#: inflating the frame count on a long plan.
SUBSTEPS = 6


def _ease(fraction: float) -> float:
    """Smoothstep: an agent accelerates out of a cell and settles into the next."""
    return fraction * fraction * (3.0 - 2.0 * fraction)


def _at(path: Sequence, frame: int, substeps: int) -> tuple[float, float]:
    step, phase = divmod(frame, substeps)
    here = path[min(step, len(path) - 1)]
    then = path[min(step + 1, len(path) - 1)]
    alpha = _ease(phase / substeps)
    return (
        here[0] + (then[0] - here[0]) * alpha,
        here[1] + (then[1] - here[1]) * alpha,
    )


def animate_paths(
    paths: Any,
    grid: Any = None,
    *,
    shape: tuple[int, int] | None = None,
    dark: bool = False,
    substeps: int = SUBSTEPS,
    trail: int = 8,
    hold: int = 12,
    title: str | None = None,
    figsize: tuple[float, float] | None = None,
    interval: int = 1000 // GIF_FPS,
) -> FuncAnimation:
    """Animate agents executing a multi-agent plan over a grid.

    Each agent glides between cells with an eased step, drags a short trail,
    and has a static goal ring drawn once. Colours come from the agent ramp by
    stable index, exactly as in :func:`planviz.draw_paths`.

    Args:
        paths: ``{name: [(row, col), ...]}`` or a sequence of paths. Paths of
            different lengths are held at their last cell, which is what a
            MAPF agent parked on its goal actually does.
        grid: optional occupancy grid to draw underneath.
        shape: ``(height, width)`` when there is no grid.
        dark: use the dark scheme.
        substeps: interpolation frames per timestep; higher is smoother.
        trail: how many timesteps of history stay visible behind each agent.
        hold: extra frames at the end so the final state is readable before a
            looping GIF restarts.
        title: axes title.
        figsize: overrides the size derived from the grid's aspect.
        interval: milliseconds between frames in an interactive backend.

    Returns:
        A :class:`~matplotlib.animation.FuncAnimation`. Keep a reference to it
        or it is garbage-collected before it renders.

    Example:
        >>> import matplotlib; matplotlib.use("Agg")
        >>> import planviz
        >>> anim = planviz.animate_paths(
        ...     {"a": [(0, 0), (0, 1), (0, 2)], "b": [(2, 2), (1, 2), (0, 2)]},
        ...     shape=(3, 3),
        ... )
        >>> sum(1 for _ in anim.new_frame_seq()) > 0
        True
    """
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation

    routes = _common.as_paths(paths)
    with style_context(dark) as tokens:
        resolved = _shape_of(grid, routes, shape)
        figure, ax = _map_axes(None, tokens, resolved, figsize)
        if grid is not None:
            _draw_obstacles(ax, grid, tokens)

        names = list(routes)
        crowded = len(names) > CROWD
        colors = (
            {name: tokens.expanded for name in names}
            if crowded
            else _common.series_colors(names, tokens)
        )
        horizon = max(len(path) for path in routes.values()) - 1

        for name in names:
            goal = routes[name][-1]
            ax.plot(
                goal[1], goal[0], markeredgecolor=colors[name], alpha=0.55,
                zorder=2, **MARKS["start"],
            )

        trails, bodies, labels = {}, {}, {}
        for name in names:
            (trails[name],) = ax.plot(
                [], [], color=colors[name], linewidth=2.4, alpha=0.5, zorder=3,
                solid_capstyle="round",
            )
            (bodies[name],) = ax.plot(
                [], [], color=colors[name], marker="o", markersize=9,
                markeredgecolor=tokens.bg_raised, markeredgewidth=1.4,
                linestyle="none", zorder=5,
            )
            if not crowded:
                labels[name] = ax.annotate(
                    name, (0, 0), textcoords="offset points", xytext=(0, 11),
                    ha="center", fontsize=8, color=tokens.muted, zorder=6,
                )

        _title(ax, tokens, title)
        clock = ax.annotate(
            "", xy=(0, 0), xycoords="axes fraction", xytext=(0, -14),
            textcoords="offset points", fontsize=9, color=tokens.muted,
            annotation_clip=False,
        )

        def update(frame: int):
            frame = min(frame, horizon * substeps)
            step = frame // substeps
            for name in names:
                path = routes[name]
                row, col = _at(path, frame, substeps)
                bodies[name].set_data([col], [row])
                if name in labels:
                    labels[name].xy = (col, row)
                history = list(path[max(0, step - trail) : step + 1]) + [(row, col)]
                trails[name].set_data(
                    [cell[1] for cell in history], [cell[0] for cell in history]
                )
            clock.set_text(f"t = {step} / {horizon}    ·    {len(names)} agents")
            return list(bodies.values()) + list(trails.values())

        animation = FuncAnimation(
            figure,
            update,
            frames=horizon * substeps + 1 + hold,
            interval=interval,
            blit=False,
        )
        # Keep notebooks from rendering the still first frame beside the player.
        plt.close(figure)
    return animation


def animate_search(
    expansions: Sequence,
    *,
    frontiers: Sequence[Sequence] | None = None,
    path: Sequence | None = None,
    grid: Any = None,
    shape: tuple[int, int] | None = None,
    start: tuple[int, int] | None = None,
    goal: tuple[int, int] | None = None,
    frames: int = 90,
    hold: int = 12,
    dark: bool = False,
    title: str | None = None,
    figsize: tuple[float, float] | None = None,
    interval: int = 1000 // GIF_FPS,
) -> FuncAnimation:
    """Animate a search: an accumulating closed list and a moving frontier.

    The expanded set never fades — it is the cost of the search. The path is
    drawn once, in the last frames, and stays.

    ``expansions`` is resampled to at most ``frames`` frames, so a 20-node
    search and a 200,000-node search produce clips of the same length.

    Args:
        expansions: cells in the order they left the open list.
        frontiers: optional open-list snapshot after each expansion, aligned
            with ``expansions``. Omit it and no frontier is drawn.
        path: the solution, revealed in the final frames.
        grid: optional occupancy grid to draw underneath.
        shape: ``(height, width)`` when there is no grid.
        start: start cell — a hollow ring, drawn from the first frame.
        goal: goal cell — a filled disc, drawn from the first frame.
        frames: maximum number of search frames before the hold.
        hold: frames the solved state is held for.
        dark: use the dark scheme.
        title: axes title.
        figsize: overrides the size derived from the grid's aspect.
        interval: milliseconds between frames in an interactive backend.

    Returns:
        A :class:`~matplotlib.animation.FuncAnimation`.

    Example:
        >>> import matplotlib; matplotlib.use("Agg")
        >>> import planviz
        >>> anim = planviz.animate_search(
        ...     [(0, 0), (0, 1), (1, 1)], path=[(0, 0), (0, 1), (1, 1)],
        ...     shape=(3, 3), frames=4,
        ... )
        >>> sum(1 for _ in anim.new_frame_seq()) > 0
        True
    """
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation

    order = np.asarray(list(expansions), dtype=float)
    if order.ndim != 2 or order.shape[1] != 2:
        raise ValueError("expansions must be a sequence of (row, col) pairs")
    total = len(order)
    solution = np.asarray(list(path), dtype=float) if path is not None else None

    with style_context(dark) as tokens:
        pool_shape = shape
        if pool_shape is None and grid is None:
            stack = order if solution is None else np.vstack([order, solution])
            pool_shape = (int(stack[:, 0].max()) + 1, int(stack[:, 1].max()) + 1)
        resolved = _shape_of(grid, None, pool_shape)
        figure, ax = _map_axes(None, tokens, resolved, figsize)
        if grid is not None:
            _draw_obstacles(ax, grid, tokens)

        (closed_art,) = ax.plot(
            [], [], color=tokens.expanded, zorder=3, **MARKS["expanded"]
        )
        (open_art,) = ax.plot(
            [], [], markeredgecolor=tokens.frontier, zorder=4, **MARKS["frontier"]
        )
        (path_art,) = ax.plot([], [], color=tokens.path, zorder=5, **MARKS["path"])
        if start is not None:
            ax.plot(
                start[1], start[0], markeredgecolor=tokens.path, zorder=6,
                **MARKS["start"],
            )
        if goal is not None:
            ax.plot(
                goal[1], goal[0], color=tokens.path,
                markeredgecolor=tokens.bg_raised, markeredgewidth=1.0, zorder=6,
                **MARKS["goal"],
            )

        _title(ax, tokens, title)
        counter = ax.annotate(
            "", xy=(0, 0), xycoords="axes fraction", xytext=(0, -14),
            textcoords="offset points", fontsize=9, color=tokens.muted,
            annotation_clip=False,
        )

        search_frames = min(max(1, frames), total)
        cuts = [
            max(1, round((i + 1) / search_frames * total))
            for i in range(search_frames)
        ]

        def update(index: int):
            step = cuts[min(index, search_frames - 1)]
            closed = order[:step]
            closed_art.set_data(closed[:, 1], closed[:, 0])
            if frontiers is not None:
                snapshot = np.asarray(
                    list(frontiers[min(step - 1, len(frontiers) - 1)]), dtype=float
                ).reshape(-1, 2)
                open_art.set_data(snapshot[:, 1], snapshot[:, 0])
            if index >= search_frames - 1 and solution is not None:
                path_art.set_data(solution[:, 1], solution[:, 0])
                open_art.set_data([], [])
                counter.set_text(
                    f"solved  ·  {total} expansions  ·  path length "
                    f"{len(solution)}"
                )
            else:
                counter.set_text(f"searching  ·  {step} / {total} expansions")
            return [closed_art, open_art, path_art, counter]

        animation = FuncAnimation(
            figure,
            update,
            frames=search_frames + hold,
            interval=interval,
            blit=False,
            repeat_delay=1200,
        )
        plt.close(figure)
    return animation


def save_animation(
    animation: FuncAnimation,
    path: str | Path,
    *,
    fps: int = GIF_FPS,
    width_px: int = GIF_WIDTH_PX,
    dpi: int | None = None,
    bitrate: int = 3200,
) -> Path:
    """Write an animation to ``.gif`` (pillow) or ``.mp4`` (ffmpeg).

    For a GIF the defaults are the brand's README cap — 12 fps, 800 px wide —
    and ``dpi`` is derived from ``width_px`` so the cap holds whatever figure
    size produced the animation. Pass ``dpi`` to override.

    Args:
        animation: a :class:`~matplotlib.animation.FuncAnimation`.
        path: destination; the suffix picks the writer.
        fps: frames per second.
        width_px: target pixel width, used to derive ``dpi``.
        dpi: explicit dots per inch, overriding ``width_px``.
        bitrate: MP4 bitrate.

    Returns:
        The :class:`~pathlib.Path` written.

    Example:
        >>> import matplotlib; matplotlib.use("Agg")
        >>> import planviz, os, tempfile
        >>> anim = planviz.animate_search([(0, 0), (1, 1)], shape=(2, 2), frames=2)
        >>> out = planviz.save_animation(
        ...     anim, os.path.join(tempfile.mkdtemp(), "search.gif")
        ... )
        >>> out.suffix
        '.gif'
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    figure = animation._fig  # the figure the animation was built on
    if dpi is None:
        dpi = max(40, int(round(width_px / figure.get_size_inches()[0])))

    if target.suffix.lower() == ".gif":
        animation.save(str(target), writer="pillow", fps=min(fps, GIF_FPS), dpi=dpi)
        return target

    import matplotlib as mpl

    try:  # a bundled ffmpeg is the difference between "works" and "install ffmpeg"
        import imageio_ffmpeg

        mpl.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # pragma: no cover - a system ffmpeg is fine too
        pass

    from matplotlib.animation import FFMpegWriter

    writer = FFMpegWriter(
        fps=fps,
        bitrate=bitrate,
        codec="libx264",
        extra_args=["-pix_fmt", "yuv420p", "-preset", "slow"],
    )
    animation.save(str(target), writer=writer, dpi=dpi)
    return target


def to_jshtml(animation: FuncAnimation) -> str:
    """Return an HTML/JS player for the animation — what a notebook shows.

    Example:
        >>> import matplotlib; matplotlib.use("Agg")
        >>> import planviz
        >>> anim = planviz.animate_search([(0, 0), (1, 1)], shape=(2, 2), frames=2)
        >>> planviz.to_jshtml(anim).lstrip().startswith("<")
        True
    """
    return animation.to_jshtml()
