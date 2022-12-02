import re

from itertools import groupby
from urllib.parse import unquote

import asyncio
from pyodide.http import pyfetch
from js import document

from lxml.html.soupparser import fromstring

from dominate.tags import table, tbody, a, tr, td

explain_url = open('explain_url.txt', 'r').read()
search_results_url = open('request_url.txt', 'r').read()


def find_in_explain_table(soup, row_name):
    for row in soup.findall('.//tr'):
        if row_name in row.text_content():
            return row.find_class('value')[0].text_content()


def extract_rhymes(poetry_raw):  # extract ending words of a poem's lines
    extracted_rhymes = []

    for idx, word in enumerate(poetry_raw):
        try:
            if poetry_raw[idx + 1] is None:
                if poetry_raw[idx]:
                    extracted_rhymes.append([idx, word])
                else:
                    extracted_rhymes.append(None)

        except IndexError:
            pass

    return extracted_rhymes


def remove_interline_breaks(response_string):
    return response_string.replace('<br/>&nbsp;', '').replace('<br/>&nbsp;', '')


def count_syllables(word):
    syllables = 'аеоиыуэюяёАЕОИЫЭУЭЮЯЁ'
    return len([letter for letter in word if letter in syllables])


def append_to_rhyme_dict(rhyme_dict, key_to_append, value_to_append):
    if key_to_append in rhyme_dict:
        rhyme_dict[key_to_append] += value_to_append
    else:
        rhyme_dict[key_to_append] = value_to_append
    return rhyme_dict


def find_bound_word(stanza, stanza_idx, main_word_symbol_idx, symbol_idx, poetry_raw, composite_rhyme):
    try:
        bound_word = stanza[stanza_idx - main_word_symbol_idx + symbol_idx][1]
        bound_word_idx = stanza[stanza_idx - main_word_symbol_idx + symbol_idx][0]
        rhyme_word = stanza[stanza_idx][1]

        if bound_word.casefold() != rhyme_word.casefold():
            if count_syllables(bound_word) == 0 \
                    or count_syllables(rhyme_word) - count_syllables(bound_word) >= 2 and composite_rhyme:

                iteration = 1
                while count_syllables(bound_word) < count_syllables(rhyme_word):
                    bound_word = poetry_raw[bound_word_idx - iteration] + ' ' + bound_word
                    iteration += 1

            return bound_word.lower()

    except (IndexError, TypeError):
        pass


async def request_handling(url):
    error_iteration = 0

    while True:
        try:
            text_data = await pyfetch(url=url, method='GET')

            if text_data.status == 200:
                return fromstring(remove_interline_breaks(await text_data.string()))

        except OSError:
            error_iteration += 1

            if error_iteration == 15:
                print('Ruscorpora does not respond.')
                raise OSError()

            await asyncio.sleep(4)

        await asyncio.sleep(1)


async def extract_text_data(text_id, url_texts):
    data_soup = await request_handling(explain_url + text_id)

    author = data_soup.find_class('value')[0].text_content()
    rhyme_type = find_in_explain_table(data_soup, 'Рифма')
    exta_parameters = find_in_explain_table(data_soup, 'Дополнительные параметры').casefold()

    multiple_rhyme_types = '#' in rhyme_type or rhyme_type.count(':') > 1
    irregular_stanza = 'нарушения строфики'.casefold() in exta_parameters
    composite_rhyme = 'составная рифма'.casefold() in exta_parameters

    if not irregular_stanza and not multiple_rhyme_types:
        rhyme_formula = rhyme_type.partition(':')[2].replace(' ', '')

        return {'id': text_id,
                'author': author,
                'rhyme_type': rhyme_formula,
                'composite_rhyme': composite_rhyme,
                'creation_year': find_in_explain_table(data_soup, 'Дата создания'),
                'links': [url for url in url_texts if text_id in unquote(url)]}


async def collect_search_pages_urls(url):
    soup_html = await request_handling(url)
    pagers = soup_html.find_class('pager')

    if pagers and len(pagers[0]) > 1:
        max_page = pagers[0].findall('.//a')[-2].text_content()

        url_pages = [url + '&p=' + str(page_number)
                     for page_number in range(int(max_page))]
    else:
        url_pages = [url]

    return url_pages


async def find_rhymes_for_word(text_data, rhyme_word):
    found_rhymes = []
    previous_soup = None
    rhyme_formula = text_data['rhyme_type']

    for url in text_data['links']:
        poetry_soup = (await request_handling(url)).find('.//tbody')

        if poetry_soup == previous_soup:
            continue

        poetry_raw = [tag.text if tag.text and 'b-wrd-expl' in tag.classes else None
                      for tag in poetry_soup.xpath('.//*[self::br or self::span]')]
        rhymes_by_stanza = [list(group) for k, group in groupby(extract_rhymes(poetry_raw), bool) if k]

        for stanza in rhymes_by_stanza:
            if len(stanza) > 1:
                for stanza_idx, word in enumerate(stanza):
                    if word[1].casefold() == rhyme_word.casefold():
                        main_word_symbol_idx = stanza_idx % len(rhyme_formula)
                        rhyme_symbol = rhyme_formula[main_word_symbol_idx]

                        if rhyme_symbol != 'х':  # that's cyrillic
                            found_rhymes += [
                                find_bound_word(stanza, stanza_idx, main_word_symbol_idx,
                                                symbol_idx, poetry_raw, text_data['composite_rhyme'])

                                for symbol_idx, symbol in enumerate(rhyme_formula)
                                if symbol == rhyme_symbol and symbol_idx != main_word_symbol_idx]

        if len(found_rhymes) >= len(text_data['links']):
            return {'author': text_data['author'],
                    'url': url,
                    'creation_year': text_data['creation_year'],
                    'rhymes': found_rhymes}
        else:
            previous_soup = poetry_soup


def update_rhymes_dict(rhymes_dict, rhymes_dict_by_author, rhymes_dict_by_year, rhymes_data):
    for found_word in rhymes_data['rhymes']:
        if found_word:
            rhymes_dict = \
                append_to_rhyme_dict(rhymes_dict, found_word,
                                     [[rhymes_data['author'], rhymes_data['url']]])
            rhymes_dict_by_author = \
                append_to_rhyme_dict(rhymes_dict_by_author, rhymes_data['author'],
                                     [[found_word, rhymes_data['url']]])
            rhymes_dict_by_year = \
                append_to_rhyme_dict(rhymes_dict_by_year, rhymes_data['creation_year'],
                                     [[found_word, rhymes_data['url'], rhymes_data['author']]])

    return rhymes_dict, rhymes_dict_by_author, rhymes_dict_by_year


def create_html_output(rhymes_dict, table_id):
    t_output = table(border=1, id=table_id, style="width:50%")

    if table_id == 'by_author':
        sorted_keys = sorted(rhymes_dict.keys(),
                             key=lambda author: re.split(r'\W+', (re.sub(r'[^а-яёА-ЯЁ ]', '', author)))[-1])
    elif table_id == 'by_year':
        sorted_keys = sorted(rhymes_dict.keys(), reverse=True,
                             key=lambda year: re.split(r'\.', year)[-1])
    else:
        sorted_keys = sorted(rhymes_dict.keys())

    with t_output.add(tbody()):
        for key in sorted_keys:
            line = tr()
            line += td(key, style="width:30%")
            values = td()
            for value in rhymes_dict[key]:
                values.add((a(value[0], href=value[1], target="_blank")))
                if len(value) > 2:
                    values.add(' (' + ' '.join(value[2:]) + ')')
            line += values

    return str(t_output)


def update_html_table(rhymes_dict, table_id):
    document.getElementById(table_id).innerHTML = create_html_output(rhymes_dict, table_id)


async def main(word):
    rhymes_dict = {}
    rhymes_dict_by_author = {}
    rhymes_dict_by_year = {}

    for url_page in await collect_search_pages_urls(search_results_url + word):
        page_soup = await request_handling(url_page)

        url_texts = ['https://processing.ruscorpora.ru' + a.attrib['href']
                     for a in page_soup.find_class('b-kwic-expl')]

        for span in page_soup.find_class('b-doc-expl'):
            text_data = await extract_text_data(span.attrib['explain'], url_texts)
            if text_data:
                rhymes_data = await find_rhymes_for_word(text_data, word)

                if rhymes_data:
                    rhymes_dict, rhymes_dict_by_author, rhymes_dict_by_year = update_rhymes_dict(
                        rhymes_dict, rhymes_dict_by_author, rhymes_dict_by_year, rhymes_data)

                    update_html_table(rhymes_dict, 'by_rhyme')
                    update_html_table(rhymes_dict_by_year, 'by_year')
                    update_html_table(rhymes_dict_by_author, 'by_author')

                    document.getElementById("sort_buttons").style.display = "block"

    search_status = 'Search completed.'
    if not rhymes_dict:
        search_status += '<br>Nothing found.'

    document.getElementById("status").innerHTML = search_status
