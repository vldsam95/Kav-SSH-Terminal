# Optional CI template

`windows-source-checks.yml` is a GitHub Actions workflow template, not an active workflow in this location.
It installs the project, runs the test suite and builds source/wheel distributions on Windows/Python 3.12.
Its actions are pinned to commits and its repository permissions are read-only.

The OAuth credential used for initial publication permits source pushes but lacks the `workflow` scope.
GitHub rejected the initial push containing an active workflow; no rejected commit was published.
A maintainer with appropriate authorization can copy this file to `.github/workflows/tests.yml` to enable it.
Local verification results are documented in PUBLICATION_REVIEW.he.md.
