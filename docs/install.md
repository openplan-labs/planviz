# Install

```bash
pip install planviz
```

!!! note "Not yet on PyPI"
    Until the first release: `pip install git+https://github.com/openplan-labs/planviz`.

Python 3.10 or newer. Two hard dependencies, both of which a plotting library
obviously needs:

| Package | Why |
| :--- | :--- |
| `matplotlib>=3.7` | the renderer |
| `numpy>=1.24` | grids, masks, and benchmark aggregation |

That is the whole list on purpose. `planviz` is meant to be safe to depend on
from a solver library, and a solver library should not drag in a plotting stack
its users did not ask for — which is why `pymapf` and `cuda-planning` both
depend on it through an extra rather than unconditionally.

## Extras

```bash
pip install 'planviz[animation]'
```

| Extra | Contents | Needed for |
| :--- | :--- | :--- |
| `animation` | `pillow`, `imageio-ffmpeg` | `save_animation(...)` — pillow writes GIFs, and the bundled ffmpeg writes MP4 without a system install |
| `dev` | `pytest`, `ruff`, `pillow`, `build`, `twine` | running the checks CI runs |
| `docs` | `mkdocs-material`, `mkdocstrings[python]` | building this site |

## Depending on it from a library

Make it an extra, and import it lazily inside the plotting module, so the
solver still runs where matplotlib cannot be installed — a Pyodide build, a
minimal container, a cluster node:

```toml
[project.optional-dependencies]
viz = ["planviz>=0.1"]
```

```python
try:
    import planviz
except ModuleNotFoundError as error:
    raise ModuleNotFoundError(
        "figures need planviz, which is optional: `pip install yourpkg[viz]`"
    ) from error
```

## Verifying an install

```python
import planviz

print(planviz.__version__)
print(planviz.tokens.SPEC_VERSION)   # the branding tokens version vendored
print(planviz.STYLE_PATH.is_file())  # the stylesheet ships inside the wheel
```

If `STYLE_PATH` is missing, the wheel was built wrong — that is exactly the
case the release workflow's wheel check exists to catch, so please
[open an issue](https://github.com/openplan-labs/planviz/issues).

## Fonts

The style asks for **Libre Franklin** and falls back to Helvetica and DejaVu
Sans. Figures render correctly without it; they just do not match the docs
typography. On Debian and Ubuntu:

```bash
sudo apt install fonts-libre-franklin && rm -rf ~/.cache/matplotlib
```

The cache removal matters — matplotlib will not notice a newly installed font
until its font list is rebuilt.
