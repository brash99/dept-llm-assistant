from pathlib import Path


class ParserRegistry:
    """
    Registry for document parsers.

    Parsers are tried in registration order. Each parser must implement:

        name
        supported_suffixes
        can_parse(path)
        parse(path, root_path)
    """

    def __init__(self):
        self._parsers = []

    def register(self, parser):
        self._parsers.append(parser)

    def get_parser(self, path):
        path = Path(path)

        for parser in self._parsers:
            if parser.can_parse(path):
                return parser

        return None

    def supported_suffixes(self):
        suffixes = set()

        for parser in self._parsers:
            suffixes.update(parser.supported_suffixes)

        return sorted(suffixes)

    def parser_names(self):
        return [parser.name for parser in self._parsers]

    def describe(self):
        return [
            {
                "name": parser.name,
                "supported_suffixes": sorted(parser.supported_suffixes),
            }
            for parser in self._parsers
        ]
