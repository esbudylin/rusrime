import argparse
import re
import sys
from argparse import Namespace
from dataclasses import dataclass
from typing import Iterator

from dataclass_csv import DataclassWriter
from rich.live import Live
from rich.table import Table

from src.poem_parser import parse_poem
from src.rhyme_extractor import extract_rhymes
from src.rnc_driver import CorpusDriver


@dataclass
class RhymeData:
    url: str
    author: str
    creation_date: str
    rhyme: str

    def generate_row(self) -> tuple[str, str, str]:
        return (
            self.author,
            self.creation_date,
            f"[link={self.url}]{self.rhyme}[/link]",
        )


class App:
    def __init__(self, args: Namespace):
        self.driver = CorpusDriver()

        columns = "Author", "Creation Date", "Rhyme"

        self.table = Table(*columns, title="Search Results", width=80)
        self.search_results: list[RhymeData] = []
        self.args = args

        word = args.word[0]

        if validate_input(word):
            self.run(word)
        else:
            raise ValueError("Search query should consist from a single word in cyrillic letters.")

    def run(self, search_word: str):
        with Live(self.table, vertical_overflow="visible"):
            for rhyme_data in self.search(search_word):
                self.search_results.append(rhyme_data)
                self.table.add_row(*rhyme_data.generate_row())

        if self.args.output:
            self.save_to_csv()

    def search(self, search_word: str) -> Iterator[RhymeData]:
        for poem_html in self.driver.search(search_word):
            poem = parse_poem(poem_html)

            if poem:
                rhymes = extract_rhymes(search_word, poem)

                md = poem.metadata
                url = self.driver.get_current_url()

                for rhyme in rhymes:
                    yield RhymeData(url, md.author, md.creation_date, rhyme)

    def save_to_csv(self):
        with open(args.output, "w", newline="", encoding="UTF-8") as f:
            w = DataclassWriter(f, self.search_results, RhymeData)
            w.write()


def validate_input(word: str) -> bool:
    return re.search("^[а-яёА-ЯЁ]+$", word) is not None


def parse_sys_args(sys_args: list[str]) -> Namespace:
    parser = argparse.ArgumentParser(
        description="rusrime: a tool for searching rhymes in the Russian National Corpus"
    )

    parser.add_argument(
        "word",
        metavar="W",
        type=str,
        nargs=1,
        help="search query: a single word in cyrillic letters",
    )

    parser.add_argument("-o", "--output", type=str, help="output CSV file name")

    return parser.parse_args(sys_args)


if __name__ == "__main__":
    args = parse_sys_args(sys.argv[1:])
    App(args)
