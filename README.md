# rusrime
Rusrime is a terminal tool designed for searching rhymes within the Russian National Corpus. The program provides rhymes for specific words based on the rhyme formulas marked in the RNC. Note that the Rusrime doesn't analyse poems with irregular and blended rhyme types, and texts with irregular stanzas are also excluded.

Rusrime is powered with Selenium as a web scraping tool, lxml as an html parser and Rich as a TUI toolkit. In addition to the terminal output, it offers the option to save a search result in a CSV file.

## installation
First, ensure you have Python installed on your device (version 3.11 or later is recommended). Once Python is installed, follow these steps:

* Clone this repository.

* Open the project directory in a terminal.

* (Optionally) Create a virtual environment.

* Run this command to install dependencies:

`pip install -r requirements.txt`

## basic usage
After dependencies are installed, you can run Rusrime. For example, to start a search for rhymes to the word 'морозец' and save the result in a 'result.csv' file, run this command:

`python main.py морозец -o result.csv`

## defining a subcorpus
Additionally, you can select a subcorpus within which to perform your search. This is useful if you want to analyze specific categories such as poems by a particular author, from a specific time period, or with a certain rhyme scheme. To do this:

* [Define the subcorpus](https://ruscorpora.ru/subcorpus?search=CgQyAggJMAE=) on the RNC website as usual.
* Return to the search page and copy the search page URL.
* Finally, paste the copied URL into the 'elements.cfg' file under the 'URL/subcorpus_url' parameter.

Note that rusrime already searches within a subcorpus of texts it can analyze. To explore the parameters of this subcorpus just open URL from 'elements.cfg' in a browser.