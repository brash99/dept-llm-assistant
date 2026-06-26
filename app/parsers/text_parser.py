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
            errors="ignore",
        )

        lines = text.splitlines()
        non_empty_lines = [line for line in lines if line.strip()]

        metadata = {
            "text_length": len(text),
            "num_lines": len(lines),
            "num_non_empty_lines": len(non_empty_lines),
            "quality": "good" if len(text.strip()) >= 100 else "poor",
            "is_empty": len(text.strip()) == 0,
        }

        return document_from_text(
            source_path=path,
            root_path=root_path,
            text=text,
            parser=self.name,
            title=path.stem,
            metadata=metadata,
        )
