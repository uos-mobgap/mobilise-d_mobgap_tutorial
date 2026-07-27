# Mobilise-D MobGap tutorial

Notebooks for running the Mobilise-D MobGap pipeline, including the OpenMovement CWA walkthrough.

## Setup

Python 3.11–3.14. **Recommended:** [uv](https://docs.astral.sh/uv/)

```bash
uv sync
```

Then open `omcwa_mobgap_walkthrough.ipynb` and select the `.venv` kernel.

### Alternative (pip)

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
```

Dependencies (`omcwa`, `mobgap` on branch `artem/cwa-loader`) are declared in `pyproject.toml`.
