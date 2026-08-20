# Contributing

Thanks for looking into planviz. Contributions are welcome, and the bar for a
useful one is low: a figure that reads badly is a bug report worth filing.

## Development setup

```bash
git clone https://github.com/openplan-labs/planviz.git
cd planviz
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev,animation,docs]'
```

Run the checks CI runs:

```bash
ruff check .
pytest                              # includes every docstring example
python scripts/sync_tokens.py --check
python examples/gallery.py          # regenerate the gallery
mkdocs build --strict
```

`pytest` renders every figure in both schemes on synthetic data and rasterizes
each one, which is where a bad colour string or an unparsable hatch shows up.
It needs no network and no GPU.

## What a figure function must do

Four contracts, each with a test in `tests/test_api.py` that will fail if a new
function breaks it:

1. **Take `dark: bool = False`.** Light and dark come from the same call.
2. **Take `ax=None`** and draw into it when given one, returning that same
   axes. Figures compose into panels; a function that always makes its own
   figure cannot.
3. **Return what it drew** — the `Axes`, or the `Figure` for a multi-panel
   figure. Never `None`.
4. **Save nothing, show nothing.** `planviz.save(...)` is the caller's call.

Beyond that:

- Draw inside `with style_context(dark) as tokens:` and stamp colours onto the
  artists. rcParams are restored when the block exits, so a colour left to the
  stylesheet will be wrong by the time the caller saves the figure.
- Import no solver type. If a function needs a `Solution` or a `SearchTrace`,
  it is in the wrong repository — take an array or a mapping instead, and put
  the adapter in the consuming project.
- Carry a docstring with an `Example:` block. `pytest` runs it.

## What a figure must look like

[`brand/figures.md`](https://github.com/openplan-labs/branding/blob/main/brand/figures.md)
is binding, and [design rules](https://openplan-labs.github.io/planviz/design-rules/)
summarises the parts this library enforces. The three that catch most PRs:

- **Never separate sets by hue alone.** Shape, hatch, fill, or connectedness
  has to carry the meaning too — every one of these repositories ends up in a
  printed paper eventually.
- **`path`, `frontier` and `expanded` are reserved words**, meaning "the
  solution", "the open list" and "the closed list". A chart that needs a second
  series takes `AGENT_RAMP`.
- **One loud line.** `highlight=` gives the argued-for series the accent;
  everything else is a supporting neutral.

## Changing the palette

Don't — not here. `planviz/tokens.py` and `planviz/styles/frontier.mplstyle`
are generated, and CI fails if they differ from
[`openplan-labs/branding`](https://github.com/openplan-labs/branding). A colour
change is a PR against that repository, followed here by:

```bash
python scripts/sync_tokens.py    # regenerate from the branding repo
python examples/gallery.py       # the gallery changes with it
```

## Style

- `ruff check .` is the arbiter.
- Public functions are typed and carry docstrings in the imperative mood
  ("Return the axes", not "Returns the axes").
- Comments explain *why*, not *what* — particularly for a magic number in a
  layout, which is otherwise unmaintainable.

## Commits and PRs

- Keep commits focused; put the *why* in the body when it is not obvious.
- A PR that changes how a figure looks should say so and, where it helps, show
  the before and after — the gallery is committed precisely so a diff is
  visible.
- A new figure type comes with: the function, its `Example:` docstring, a test
  in `tests/test_figures.py`, an entry in `examples/gallery.py`, a section in
  `docs/gallery.md`, and a line in `CHANGELOG.md`.
