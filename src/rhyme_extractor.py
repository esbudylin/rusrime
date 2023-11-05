from dataclasses import dataclass
from typing import Optional

from src.poem_parser import Line, Poem, Stanza


@dataclass
class BoundWord:
    bound_word: str
    bound_line_id: int


def extract_rhymes(main_word: str, poem: Poem) -> set[str]:
    md = poem.metadata

    found_rhymes = []

    line_endings = extract_line_endings(poem.stanzas)

    for stanza_id, stanza_endings in enumerate(line_endings):
        for line_id, word in enumerate(stanza_endings):
            if word.casefold() == main_word.casefold():
                main_symbol_id = line_id % len(md.rhyme_formula)
                main_symbol = md.rhyme_formula[main_symbol_id]

                if main_symbol == "х":  # that's cyrillic
                    continue

                for symbol_id, symbol in enumerate(md.rhyme_formula):
                    if symbol == main_symbol and symbol_id != main_symbol_id:
                        bw = find_bound_word(stanza_endings, line_id, main_symbol_id, symbol_id)

                        if not bw:
                            continue

                        if should_compose_rhyme(main_word, bw.bound_word, md.composite_rhyme):
                            bound_line = poem.stanzas[stanza_id][bw.bound_line_id]

                            bw.bound_word = add_composite_rhyme(
                                main_word, bw.bound_word, bound_line
                            )

                        found_rhymes.append(bw.bound_word)

    return set(found_rhymes)


def find_bound_word(
    stanza_endings: list[str], line_id: int, main_symbol_id: int, symbol_id: int
) -> Optional[BoundWord]:
    bound_line_id = line_id - main_symbol_id + symbol_id
    rhyme_word = stanza_endings[line_id]

    try:
        bound_word = stanza_endings[bound_line_id]

    except IndexError:
        return None

    if bound_word.casefold() != rhyme_word.casefold():
        return BoundWord(bound_word.lower(), bound_line_id)


def should_compose_rhyme(main_word: str, bound_word: str, composite_rhyme: bool) -> bool:
    return (
        count_syllables(bound_word) == 0
        or len(bound_word) == 1
        or count_syllables(main_word) - count_syllables(bound_word) >= 2
        and composite_rhyme
    )


def add_composite_rhyme(main_word: str, bound_word: str, line: Line) -> str:
    for word in line[-2::-1]:
        bound_word = word + " " + bound_word

        if count_syllables(bound_word) >= count_syllables(main_word):
            break

    return bound_word


def extract_line_endings(stanzas: list[Stanza]) -> list[list[str]]:
    res = []

    for stanza in stanzas:
        res.append([line[-1] for line in stanza if line])

    return res


def count_syllables(word: str) -> int:
    syllables = "аеоиыуэюяё"
    return len([letter for letter in word if letter.casefold() in syllables])
