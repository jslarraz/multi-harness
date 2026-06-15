---
name: publish
description: Bump the package version in pyproject.toml, rebuild the wheel and sdist, and publish to PyPI. Use when the user asks to publish, release, bump version, or ship a new version.
argument-hint: [patch|minor|major|<x.y.z>]
allowed-tools: [Read, Edit, Bash]
---

# Publish to PyPI

Bump the version, build, and publish this package to PyPI.

## Arguments

The user invoked this with: $ARGUMENTS

Interpret the argument as:
- `patch` (default if omitted) — increment the Z in x.y.Z
- `minor` — increment the Y in x.Y.0, reset Z to 0
- `major` — increment the X in X.0.0, reset Y and Z to 0
- A literal version string like `1.2.3` — use it exactly

## Steps

### 1. Read the current version

Read `pyproject.toml` and extract the current `version = "x.y.z"` value.

### 2. Compute the new version

Apply the bump type from $ARGUMENTS (default: `patch`) to derive the new version string.
If the argument is already a dotted version string, use it as-is.

Show the user: `Bumping x.y.z → x.y.z+1` and ask for confirmation before proceeding.

### 3. Update pyproject.toml

Use Edit to replace the version line in `pyproject.toml`:
```
version = "<old>"
```
→
```
version = "<new>"
```

### 4. Rebuild the distribution

```bash
rm -rf dist/
.venv/bin/python -m build
```

Verify both `dist/*.whl` and `dist/*.tar.gz` were produced.

### 5. Publish to PyPI

Load credentials from `.env` and upload:

```bash
set -a && source .env && set +a && .venv/bin/twine upload dist/*
```

The `.env` file must contain `TWINE_USERNAME` and `TWINE_PASSWORD`. If it is missing or
the upload fails with an auth error, tell the user to check `.env`.

### 6. Commit the version bump

Stage and commit only `pyproject.toml`:

```bash
git add pyproject.toml
git commit -m "chore: bump version to <new>"
```

### 7. Report

Print the PyPI URL from twine's output (format: `View at: https://pypi.org/project/.../`).
