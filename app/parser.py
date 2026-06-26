from abc import ABC, abstractmethod
from pathlib import Path


class Parser(ABC):
    name = "BaseParser"
    supported_suffixes = set()

    def can_parse(self, path):
        return Path(path).suffix.lower() in self.supported_suffixes

    @abstractmethod
    def parse(self, path, root_path):
        pass
