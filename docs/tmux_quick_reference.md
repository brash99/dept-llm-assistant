# tmux Quick Reference

## 1. Start a new tmux session

``` bash
tmux new -s rag
```

You can replace `rag` with any session name.

------------------------------------------------------------------------

## 2. Activate your environment

``` bash
cd ~/dept-llm-assistant
source .venv/bin/activate
```

------------------------------------------------------------------------

## 3. Start the long-running job

``` bash
python scripts/build_vector_db.py --limit 1000000
```

or

``` bash
streamlit run web_app.py
```

------------------------------------------------------------------------

## 4. Detach

Press:

1.  `Ctrl-b`
2.  Then `d`

The process keeps running.

------------------------------------------------------------------------

## 5. Disconnect

You can safely log out. The tmux session continues to run.

------------------------------------------------------------------------

## 6. List sessions

``` bash
tmux ls
```

------------------------------------------------------------------------

## 7. Reattach

``` bash
tmux attach -t rag
```

or

``` bash
tmux a -t rag
```

------------------------------------------------------------------------

## 8. Multiple windows

Create a new window:

    Ctrl-b c

Next / previous:

    Ctrl-b n
    Ctrl-b p

Jump directly:

    Ctrl-b 0
    Ctrl-b 1
    Ctrl-b 2

Example layout:

    Window 0: build_vector_db.py
    Window 1: htop
    Window 2: nvidia-smi
    Window 3: git
    Window 4: testing

------------------------------------------------------------------------

## 9. End the session

Inside tmux:

``` bash
exit
```

Or outside:

``` bash
tmux kill-session -t rag
```

------------------------------------------------------------------------

# Everyday Commands

``` bash
tmux new -s rag
Ctrl-b d
tmux ls
tmux a -t rag
tmux kill-session -t rag
```
