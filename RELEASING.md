# Releasing

`planviz` publishes to PyPI from a tag, through
[`.github/workflows/release.yml`](.github/workflows/release.yml). The workflow
authenticates with [Trusted Publishing][tp], so no API token is stored in the
repository.

[tp]: https://docs.pypi.org/trusted-publishers/

## One-time PyPI setup

The project does not exist on PyPI yet, so the first release needs a *pending*
publisher — a trusted publisher declared before the project's first upload.

1. Sign in to PyPI → **Your projects** → **Publishing** →
   <https://pypi.org/manage/account/publishing/>.
2. Under "Add a new pending publisher", fill in:

   | Field | Value |
   | :--- | :--- |
   | PyPI project name | `planviz` |
   | Owner | `openplan-labs` |
   | Repository name | `planviz` |
   | Workflow name | `release.yml` |
   | Environment name | `pypi` |

3. Repeat on [TestPyPI](https://test.pypi.org/manage/account/publishing/) with
   environment `testpypi`, which enables the rehearsal below.

The environment names matter: the workflow's publish jobs run in GitHub
environments called `pypi` and `testpypi` (both already created on this
repository), and PyPI checks that claim in the OIDC token. Adding required
reviewers to the `pypi` environment in **Settings → Environments** is worth
doing — it turns "push a tag" into "push a tag, then approve", which is a
useful pause before an irreversible upload.

## Rehearse

**Actions → Release → Run workflow**, target `testpypi`. This builds, checks
and smoke-tests exactly as a real release does, then uploads to TestPyPI,
where a version number can be spent freely.

## Release

1. Update `__version__` in `planviz/__init__.py`.
2. Update `version:` and `date-released:` in [`CITATION.cff`](CITATION.cff).
3. Add the version's section to [`CHANGELOG.md`](CHANGELOG.md) — the workflow
   copies it verbatim into the GitHub release notes, so write it for a reader
   deciding whether to upgrade.
4. Regenerate the gallery if any figure changed:

   ```sh
   python examples/gallery.py && git add docs/assets/gallery
   ```

5. **First release only** — the README and the install page currently tell the
   truth about a package that is not on PyPI yet. Make them tell the truth
   about one that is:

   - Replace the placeholder badge

     ```
     [![PyPI](https://img.shields.io/badge/PyPI-not%20yet%20published-6d8298)](https://openplan-labs.github.io/planviz/install/)
     ```

     with the live one

     ```
     [![PyPI](https://img.shields.io/pypi/v/planviz?color=c2472c)](https://pypi.org/project/planviz/)
     ```

   - Delete the "Not yet on PyPI — until then: `pip install git+…`" line from
     the README and the matching admonition in `docs/install.md`.

6. Commit, then tag and push:

   ```sh
   git commit -am "Release 0.1.0"
   git tag v0.1.0
   git push origin main v0.1.0
   ```

The workflow then builds the sdist and wheel, fails if the tag disagrees with
`planviz.__version__`, runs `twine check --strict`, verifies the wheel carries
the vendored stylesheet and tokens, re-checks those tokens against the
branding repository, installs the built wheel on Python 3.10–3.13 and renders a
figure with it, publishes to PyPI, and finally creates the GitHub release with
the distributions attached.

## What the checks are protecting against

- **Tag/version drift** — a tag that disagrees with the package version ships
  an artifact whose name lies about its contents, and PyPI uploads cannot be
  replaced.
- **A wheel without the brand** — `planviz/styles/frontier.mplstyle` and
  `planviz/tokens.py` are the whole point of vendoring. A wheel missing them
  installs cleanly and renders every figure in matplotlib's defaults.
- **Palette drift** — a release is the worst moment to discover the vendored
  palette no longer matches
  [`openplan-labs/branding`](https://github.com/openplan-labs/branding),
  because the figures a user renders are the ones this wheel carries, forever.
- **Style leaking into a caller** — the smoke test asserts that rendering a
  figure leaves `rcParams` untouched, on a fresh interpreter, from the
  installed wheel. That contract is what lets a solver library depend on this
  one.
- **A wheel that only works in the source tree** — the smoke test runs from a
  temporary directory, so a missing package-data entry cannot hide behind the
  checkout.

## Versioning

[SemVer](https://semver.org/). While the API is at `0.x`, minor versions may
break it; the changelog says so when they do.

A change in *how a figure looks* — a new mark, a different default, a palette
update pulled from the branding repository — is a **minor** version, not a
patch. Downstream repositories commit their rendered figures, so a visual
change shows up in their diffs and deserves a version number that warns them.
