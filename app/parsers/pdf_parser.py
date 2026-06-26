from pathlib import Path
import fitz  # PyMuPDF

from app.parser import Parser
from app.knowledge import document_from_text


class PDFParser(Parser):
    name = "PDFParser"
    supported_suffixes = {".pdf"}

    def parse(self, path, root_path):
        path = Path(path)

        text_parts = []
        metadata = {
            "num_pages": 0,
            "page_lengths": [],
        }

        with fitz.open(path) as pdf:
            metadata["num_pages"] = pdf.page_count

            for i, page in enumerate(pdf):
                page_text = page.get_text("text")
                text_parts.append(f"\n\n--- Page {i + 1} ---\n\n{page_text}")
                metadata["page_lengths"].append(len(page_text))

            pdf_metadata = pdf.metadata or {}
            metadata["pdf_metadata"] = pdf_metadata

            title = pdf_metadata.get("title") or path.stem

        text = "\n".join(text_parts).strip()
        metadata["text_length"] = len(text)
        metadata["is_probably_scanned"] = len(text.strip()) < 50

        return document_from_text(
            source_path=path,
            root_path=root_path,
            text=text,
            parser=self.name,
            title=title,
            metadata=metadata,
        )
