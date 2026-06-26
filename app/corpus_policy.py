from pathlib import Path


class CorpusPolicy:

    def __init__(self, config):
        corpus = config.get("corpus", {})

        self.exclude_paths = corpus.get("exclude_paths", [])
        self.exclude_extensions = corpus.get("exclude_extensions", [])
        self.exclude_hidden = corpus.get("exclude_hidden", True)

    def should_include(self, path, root):
        rel = Path(path).relative_to(root).as_posix()
        name = Path(path).name

        if self.exclude_hidden and name.startswith("."):
            return False

        if name.startswith("._") or name == ".DS_Store":
            return False

        if Path(path).suffix.lower() in self.exclude_extensions:
            return False

        for excluded in self.exclude_paths:
            if rel == excluded or rel.startswith(excluded.rstrip("/") + "/"):
                return False

        return True
