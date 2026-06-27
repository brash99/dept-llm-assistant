from pathlib import Path
import shutil
import subprocess

from app.parser import Parser
from app.knowledge import document_from_text
from app.parsers.docx_parser import DOCXParser
from app.parsers.pptx_parser import PPTXParser
from app.parsers.xlsx_parser import XLSXParser


class LegacyOfficeParser(Parser):
    name = "LegacyOfficeParser"
    supported_suffixes = {".doc", ".ppt", ".xls"}

    def __init__(self):
        self.dispatch = {
            ".doc": ("docx", DOCXParser()),
            ".ppt": ("pptx", PPTXParser()),
            ".xls": ("xlsx", XLSXParser()),
        }

    def parse(self, path, root_path):
        path = Path(path)
        root_path = Path(root_path)

        suffix = path.suffix.lower()
        if suffix not in self.dispatch:
            raise ValueError(f"Unsupported legacy Office file: {path}")

        target_ext, modern_parser = self.dispatch[suffix]

        soffice = shutil.which("soffice") or shutil.which("libreoffice")
        if soffice is None:
            raise RuntimeError("LibreOffice/soffice not found on PATH")

        cache_dir = (
            root_path.parent
            / "cache"
            / "libreoffice_converted"
            / path.relative_to(root_path).parent
        )
        cache_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            soffice,
            "--headless",
            "--convert-to",
            target_ext,
            "--outdir",
            str(cache_dir),
            str(path),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"LibreOffice conversion failed for {path}\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )

        converted_path = cache_dir / f"{path.stem}.{target_ext}"

        if not converted_path.exists():
            raise RuntimeError(
                f"Converted file not found: {converted_path}\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )

        converted_doc = modern_parser.parse(converted_path, cache_dir)

        metadata = dict(converted_doc.metadata)
        metadata["legacy_conversion"] = {
            "original_suffix": suffix,
            "converted_suffix": f".{target_ext}",
            "converted_path": str(converted_path),
            "conversion_tool": "LibreOffice",
            "conversion_stdout": result.stdout.strip(),
            "conversion_stderr": result.stderr.strip(),
            "modern_parser": modern_parser.name,
        }

        return document_from_text(
            source_path=path,
            root_path=root_path,
            text=converted_doc.text,
            parser=self.name,
            title=converted_doc.title or path.stem,
            metadata=metadata,
        )
