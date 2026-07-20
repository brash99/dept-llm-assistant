# tmux Quick Reference for the A100

Use tmux for long-running server processes under the canonical checkout:

```bash
cd /work/brash/dept-llm-assistant
tmux new -s iso
source .venv/bin/activate
```

## Suggested windows

- Window 0: deployment-managed LLM server
- Window 1: `streamlit run web_app.py`
- Window 2: `nvidia-smi` or `nvidia-smi dmon`
- Window 3: ingestion, chunking, embeddings, or index builds
- Window 4: tests and Git inspection

Create and navigate windows:

```text
Ctrl-b c        create window
Ctrl-b n        next window
Ctrl-b p        previous window
Ctrl-b 0..9     select window
```

Detach without stopping processes:

```text
Ctrl-b d
```

List and reattach:

```bash
tmux ls
tmux attach -t iso
```

Stop a session intentionally:

```bash
tmux kill-session -t iso
```

Use the current individual pipeline stages:

```bash
.venv/bin/python -m scripts.chunk_documents --limit 1000000
.venv/bin/python -m scripts.embed_chunks --limit 1000000 --embedding-context title_path
.venv/bin/python -m scripts.build_vector_index
```

See [A100 Operations](../operations/a100.md) for ordering and safety notes.
