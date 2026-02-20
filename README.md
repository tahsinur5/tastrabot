## tastrabot

Personal trading bot for US stocks (Telegram alerts + periodic reports).

### Local setup (Python 3.11+)

Preferred: `uv` (fast, simple; no Poetry).

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env
```

### Run tests

```bash
uv run pytest
```

### Secrets

- Keep real secrets in `.env` only (it is ignored by git).
- Prefer OSS and services with free tiers unless explicitly upgrading (see `docs/plan.md`).

### Notes

- If you don’t have `uv`: `brew install uv` (macOS) or see the `uv` docs for other platforms.
- Fallback (no `uv`): use `python -m venv .venv` + `pip install -e ".[dev]"`.
