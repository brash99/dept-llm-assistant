from pathlib import Path

from app.parser import Parser
from app.knowledge import document_from_text


class TextParser(Parser):
    name = "TextParser"
    supported_suffixes = {
        ".txt",
        ".md",
        ".csv",
        ".tex",
        ".log",
        ".json",
        ".xml",
        ".html",
        ".htm",
    }

    def parse(self, path, root_path):
        path = Path(path)

        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        metadata = {
            "encoding": "utf-8",
            "text_length": len(text),
            "num_lines": text.count("\n") + 1 if text else 0,
        }

        return document_from_text(
            source_path=path,
            root_path=root_path,
            text=text,
            parser=self.name,
            title=path.stem,
            metadata=metadata,
        )
