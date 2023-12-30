from dataclasses import dataclass
from typing import Optional

from lxml.html.soupparser import fromstring

from src.config import classes, xpath
from src.rnc_driver import PoemHtml


@dataclass
class PoemMetadata:
    author: str
    creation_date: str
    rhyme_formula: str
    composite_rhyme: bool
    stanza_len: Optional[int]


Line = list[str]
Stanza = list[Line]


@dataclass
class Poem:
    metadata: PoemMetadata
    stanzas: list[Stanza]


def parse_poem(poem_data: PoemHtml) -> Optional[Poem]:
    metadata = parse_metadata(poem_data.explain_table)

    if metadata:
        stanzas = parse_stanzas(poem_data.text, metadata.stanza_len)
        composed_stanzas = compose_stanzas(stanzas, metadata.rhyme_formula)

        return Poem(metadata, composed_stanzas)


def parse_stanzas(text: str, stanza_len: Optional[int]) -> list[Stanza]:
    soup = fromstring(text)

    result = []
    current_stanza: Stanza = []

    for i, line in enumerate(soup.xpath(xpath["poem_line"])):
        line_classes = line.get("class")

        line_text = parse_line(line)

        new_stanza = len(current_stanza) == 0
        text_header = i == 0
        staza_end_or_beginning = classes["separator_line"] in line_classes

        digit_line = all(i.isdigit() for i in line_text)

        if staza_end_or_beginning:
            if digit_line:
                continue

            if not text_header:
                current_stanza.append(line_text)

                if not new_stanza:
                    delete_stanza_header(current_stanza, stanza_len)

                    result.append(current_stanza)
                    current_stanza = []

        else:
            current_stanza.append(line_text)

    if current_stanza:
        delete_stanza_header(current_stanza, stanza_len)
        result.append(current_stanza)

    return result


def compose_stanzas(stanzas: list[Stanza], rhyme_formula: str) -> list[Stanza]:
    stanza_len = len(rhyme_formula)

    acc = [[]]

    for stanza in stanzas:
        if len(acc[-1]) < stanza_len:
            acc[-1].extend(stanza)
        else:
            acc.append(stanza)

    return acc


def delete_stanza_header(current_stanza: Stanza, stanza_len: Optional[int]):
    stanza_header = len(current_stanza[0]) == 1 and (
        current_stanza[0][0].isdigit() or stanza_len and len(current_stanza) == stanza_len + 1
    )

    if stanza_header:
        del current_stanza[0]


def parse_metadata(explain_table: str) -> Optional[PoemMetadata]:
    soup = fromstring(explain_table)

    params_to_fetch = (
        "Автор",
        "Дата создания",
        "Рифма",
        "Дополнительные параметры",
        "Графическая строфика",
        "Строфика",
    )

    author, creation_date, rhyme_type, exta_parameters, graphic_stanza, stanza = [
        find_in_explain_table(soup, p) for p in params_to_fetch
    ]

    multiple_rhyme_types = "#" in rhyme_type or rhyme_type.count(":") > 1

    exta_parameters = exta_parameters.casefold()

    irregular_stanza = "нарушения строфики" in exta_parameters
    composite_rhyme = "составная рифма" in exta_parameters

    if not irregular_stanza and not multiple_rhyme_types:
        rhyme_formula = rhyme_type.partition(":")[2].replace(" ", "")

        stanza_data = graphic_stanza if graphic_stanza else stanza

        stanza_str = stanza_data.partition(":")[0].strip()
        stanza_len = int(stanza_str) if stanza_str.isdigit() else None

        if rhyme_formula:
            return PoemMetadata(author, creation_date, rhyme_formula, composite_rhyme, stanza_len)


def find_in_explain_table(soup, row_name) -> str:
    for row in soup.findall(".//tr"):
        if row_name in row.text_content():
            return row.find_class(classes["table_value"])[0].text_content()

    return ""


def parse_line(soup) -> Line:
    return [word.text_content() for word in soup.find_class(classes["word"])]
