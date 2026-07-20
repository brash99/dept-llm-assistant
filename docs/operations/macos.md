# macOS Development

These instructions apply to a local macOS checkout used for editing, review, and lightweight tests. The canonical production checkout remains `/work/brash/dept-llm-assistant` on the A100 server.

## Setup

From the local checkout root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m pip install -r requirements-dev.txt
```

GPU-specific dependencies or the production FAISS index may be unavailable locally. Do not change production configuration paths merely to make a local command run. Presentation and deterministic contract tests are designed to avoid loading retrieval dependencies when possible.

## Routine local validation

```bash
python3 -m compileall -q app scripts
python3 -m pytest -q
git diff --check
git status -sb
```

If optional retrieval dependencies are absent, run the dependency-light focused tests documented in [Testing](testing.md), then run GPU/index tests on the A100 before deployment.

## Local UI

A local Streamlit process can render only when its configured dependencies and data are available:

```bash
source .venv/bin/activate
streamlit run web_app.py
```

The repository configuration uses the canonical A100 root and local LLM endpoint. Prefer a separate, uncommitted local configuration strategy rather than committing macOS paths or model settings.

## Git workflow

Inspect before synchronizing:

```bash
git status -sb
git fetch origin
git log --oneline --decorate --graph --max-count=20 --all
```

Update a clean branch with fast-forward-only semantics:

```bash
git pull --ff-only origin "$(git branch --show-current)"
```

Before asking for review:

```bash
git diff --check
git status --short
```

Do not assume a local test against placeholder storage validates production retrieval.
