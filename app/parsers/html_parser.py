from pathlib import Path

from bs4 import BeautifulSoup

from app.parser import Parser
from app.knowledge import document_from_text


class HTMLParser(Parser):

    name = "HTMLParser"

    supported_suffixes = {
        ".html",
        ".htm",
    }

    def parse(self, path, root_path):

        path = Path(path)

        with path.open(
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as f:
            soup = BeautifulSoup(f, "html.parser")

        # Remove things that are not document content
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = soup.get_text(
            separator="\n",
            strip=True
        )

        text_length = len(text)

        metadata = {
            "title": "",
            "num_links": len(soup.find_all("a")),
            "num_images": len(soup.find_all("img")),
            "text_length": text_length,
            "quality": "good" if text_length >= 100 else "poor",
            "is_empty": text_length == 0,
        }

        if soup.title and soup.title.string:
            metadata["title"] = soup.title.string.strip()
            title = metadata["title"]
        else:
            title = path.stem

        return document_from_text(
            source_path=path,
            root_path=root_path,
            text=text,
            parser=self.name,
            title=title,
            metadata=metadata,
        )
