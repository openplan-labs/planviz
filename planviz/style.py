"""Applying the Frontier matplotlib style, in light and dark.

The stylesheet ships inside the wheel (``planviz/styles/frontier.mplstyle``), so
nothing here touches the network and no consumer has to locate the branding
repository at runtime.

Importing :mod:`planviz` changes no global state. The style is applied only when
you ask for it — either permanently with :func:`use_style`, or for the duration
of a block with :func:`style_context`. Every figure function in the library
draws inside a :func:`style_context` and additionally stamps the resolved
colours onto the artists it creates, so a returned figure keeps its appearance
after the context has closed.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from . import tokens as _tokens
from .tokens import Tokens

__all__ = ["STYLE_PATH", "use_style", "style_context", "rc_params"]

#: Absolute path to the vendored stylesheet. Usable directly with
#: ``matplotlib.pyplot.style.use(planviz.STYLE_PATH)``.
STYLE_PATH: Path = Path(__file__).resolve().parent / "styles" / "frontier.mplstyle"


def rc_params(dark: bool = False) -> dict[str, Any]:
    """Return the rcParams that turn the light stylesheet into ``dark``.

    The vendored stylesheet is the light scheme — light-first is the brand's
    position, because papers, READMEs and notebooks all default to a light
    ground. Dark mode is that stylesheet plus this overlay.

        >>> import planviz
        >>> planviz.style.rc_params(dark=True)["axes.facecolor"]
        '#1a2126'
        >>> planviz.style.rc_params(dark=False)
        {}
    """
    if not dark:
        return {}
    t = _tokens.DARK
    return {
        "figure.facecolor": t.bg,
        "figure.edgecolor": t.bg,
        "savefig.facecolor": t.bg,
        "savefig.edgecolor": t.bg,
        "axes.facecolor": t.bg_raised,
        "axes.edgecolor": t.line,
        "axes.labelcolor": t.body,
        "axes.titlecolor": t.heading,
        "grid.color": t.line,
        "xtick.color": t.muted,
        "ytick.color": t.muted,
        "xtick.labelcolor": t.muted,
        "ytick.labelcolor": t.muted,
        "text.color": t.body,
    }


def use_style(dark: bool = False) -> Tokens:
    """Apply the Frontier style to matplotlib's global rcParams; return tokens.

    Use this once at the top of a notebook or a script, so figures you draw by
    hand match the ones this library draws. It is a deliberate, explicit call:
    importing ``planviz`` on its own leaves matplotlib untouched.

        >>> import matplotlib
        >>> matplotlib.use("Agg")
        >>> import matplotlib.pyplot as plt, planviz
        >>> t = planviz.use_style(dark=True)
        >>> t.mode
        'dark'
        >>> plt.rcParams["axes.facecolor"]
        '#1a2126'
        >>> plt.rcdefaults()
    """
    import matplotlib.pyplot as plt

    plt.style.use(str(STYLE_PATH))
    plt.rcParams.update(rc_params(dark))
    return _tokens.get(dark)


@contextmanager
def style_context(dark: bool = False) -> Iterator[Tokens]:
    """Apply the Frontier style for the duration of a block; yield its tokens.

    rcParams are restored on exit, which is what keeps a library call from
    reaching into a caller's notebook.

        >>> import matplotlib
        >>> matplotlib.use("Agg")
        >>> import matplotlib.pyplot as plt, planviz
        >>> before = plt.rcParams["axes.facecolor"]
        >>> with planviz.style_context() as t:
        ...     figure_facecolor = plt.rcParams["figure.facecolor"]
        >>> t.path
        '#c2472c'
        >>> plt.rcParams["axes.facecolor"] == before
        True
    """
    import matplotlib.pyplot as plt

    with plt.style.context(str(STYLE_PATH)):
        with plt.rc_context(rc_params(dark)):
            yield _tokens.get(dark)
