# Copilot / coding-agent instructions

See [AGENTS.md](../AGENTS.md) at the repository root for the full development
guide, architecture rules and definition of done.

Quick reference:

- Install: `python -m pip install -e ".[dev]"`
- Verify: `python scripts/dev.py check`
- Offline tests only; use `tests/fakes.py`.
- Layering: `core → api → services → reporting/ui/cli`; `charts` is a leaf beside
  `core`. Enforced by `tests/architecture/test_layers.py`.
- Never import Matplotlib at module scope under `src/bangumi_catcher/ui/`.
- Exports must be atomic and must preserve existing files on failure.
