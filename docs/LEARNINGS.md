# What fought back

A running log of surprises, wrong assumptions and fixes, written as they happen. It feeds the Builder
Center blog post.

## Thu 8 Oct 2026 (kickoff)

### A 43 KB/s network decides the Python version
The venue network measured about 43 KB/s to PyPI, so `uv sync` sat resolving for 10 minutes. The local uv
cache already held wheels for Python 3.12 (which the spec asks for, and Lambda supports), so the project
pins 3.12 and the first sync ran with `--offline` in seconds. Lesson: on a slow link, resolve and download
once, then work offline.

### GitHub over HTTPS
The machine had no SSH key registered with GitHub, so the first push failed. The repo uses HTTPS with the
GitHub CLI as its credential helper (`git config credential.helper '!gh auth git-credential'`).
