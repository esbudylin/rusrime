from dataclasses import dataclass
from typing import Iterator

from selenium import webdriver
from selenium.common.exceptions import (ElementClickInterceptedException,
                                        NoSuchElementException,
                                        TimeoutException)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from src.config import search_url, xpath

WAIT_TIME = 100


@dataclass
class PoemHtml:
    explain_table: str
    text: str


class CorpusDriver(webdriver.Chrome):
    def __init__(self):
        service = Service(ChromeDriverManager().install())

        options = Options()
        options.add_argument("--headless")
        options.add_argument("log-level=3")

        super().__init__(options, service)

        self.ongoing_search: bool = False

        width = 2000
        height = 5000
        self.set_window_size(width, height)

    def search(self, word: str) -> Iterator[PoemHtml]:
        self.__start_search(word)

        while self.ongoing_search:
            for poem_data in self.__collect_poem_data():
                yield poem_data

            self.__next_search_page()

    def __start_search(self, word: str):
        self.get(search_url)

        self.__close_onboarding()
        self.__set_additional_features()

        self.find_element(By.XPATH, xpath["wordform_input"]).send_keys(word)
        self.find_element(By.XPATH, xpath["search_button"]).click()

        WebDriverWait(self, WAIT_TIME).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".search-result-fail, .concordance-list")
            )
        )

        if not self.find_elements(By.CLASS_NAME, "search-result-fail"):
            WebDriverWait(self, WAIT_TIME).until(
                EC.presence_of_element_located((By.CLASS_NAME, "concordance-list"))
            )

            self.ongoing_search = True

    def __next_search_page(self):
        forward_button = (By.CSS_SELECTOR, '[aria-label="Вперед"]')

        def refresh_page():
            self.refresh()
            WebDriverWait(self, WAIT_TIME).until(EC.presence_of_element_located(forward_button))
            self.__next_search_page()

        try:
            self.find_element(*forward_button).click()

        except ElementClickInterceptedException:
            self.ongoing_search = False
            return

        try:
            loader_element = self.find_element(By.CLASS_NAME, "results-page-loader")

            try:
                WebDriverWait(self, WAIT_TIME).until(EC.staleness_of(loader_element))

            except TimeoutException:
                refresh_page()

        except NoSuchElementException:
            try:
                WebDriverWait(self, WAIT_TIME).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "concordance-list"))
                )

            except TimeoutException:
                refresh_page()

    def __collect_poem_data(self) -> Iterator[PoemHtml]:
        buttons = self.find_elements(By.CLASS_NAME, "result-actions__context")
        search_window = self.current_window_handle

        previous_url = None

        for button in buttons:
            cur_windows = len(self.window_handles)

            button.click()
            WebDriverWait(self, WAIT_TIME).until(EC.number_of_windows_to_be(cur_windows + 1))
            self.switch_to.window(self.window_handles[-1])

            if self.current_url != previous_url:
                text_source = self.__extract_text_source()
                explain_table = self.__extract_explain_table()

                yield PoemHtml(explain_table, text_source)

            previous_url = self.current_url

            self.close()
            self.switch_to.window(search_window)

    def __extract_text_source(self):
        text_item = (By.CLASS_NAME, "concordance-item")

        WebDriverWait(self, WAIT_TIME).until(EC.presence_of_element_located(text_item))

        return self.find_element(*text_item).get_attribute("innerHTML")

    def __extract_explain_table(self):
        explain_table_button = self.find_element(By.XPATH, xpath["explain_table_button"])
        explain_table_button.click()

        explain_table = (By.CLASS_NAME, "explain__content")

        WebDriverWait(self, WAIT_TIME).until(EC.presence_of_element_located(explain_table))

        return self.find_element(*explain_table).get_attribute("innerHTML")

    def __close_onboarding(self):
        try:
            close_button = self.find_element(By.XPATH, xpath["close_onboarding"])
            close_button.click()
            WebDriverWait(self, WAIT_TIME).until(EC.invisibility_of_element(close_button))

        except NoSuchElementException:
            pass

    def __set_additional_features(self):
        self.find_element(By.XPATH, xpath["additional_features"]).click()

        apply_features = (By.CSS_SELECTOR, "[aria-label='Применить']")

        WebDriverWait(self, WAIT_TIME).until(EC.presence_of_element_located(apply_features))

        self.find_element(By.XPATH, xpath["rhyme_zone"]).click()

        self.find_element(*apply_features).click()
