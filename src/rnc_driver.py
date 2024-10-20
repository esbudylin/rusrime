from dataclasses import dataclass
from typing import Iterator

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from seleniumbase import Driver

from src.config import search_url, xpath

WAIT_TIME = 100


@dataclass
class PoemHtml:
    explain_table: str
    text: str


class CorpusDriver:
    def __init__(self):
        self.driver = Driver(
            browser="chrome",
            headless=True,
            locale_code="ru",
            d_width=2000,
            d_height=5000,
        )

        self.ongoing_search: bool = False

    def get_current_url(self):
        return self.driver.current_url

    def search(self, word: str) -> Iterator[PoemHtml]:
        self.__start_search(word)

        while self.ongoing_search:
            yield from self.__collect_poem_data()
            self.__next_search_page()

    def __start_search(self, word: str):
        import time

        self.driver.get(search_url)

        # I haven't figured out a cleaner way to make it work. Checking for document.ReadyState and presence of elements doesn't work,
        # since at a certain point in page loading, elements can be present, but the interaction with them will not yield a desirable result.
        time.sleep(3)

        self.__close_onboarding()
        self.__set_additional_features()

        self.driver.find_element(By.XPATH, xpath["wordform_input"]).send_keys(word)
        self.driver.find_element(By.XPATH, xpath["search_button"]).click()

        WebDriverWait(self.driver, WAIT_TIME).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".search-result-fail, .concordance-list")
            )
        )

        if not self.driver.find_elements(By.CLASS_NAME, "search-result-fail"):
            WebDriverWait(self.driver, WAIT_TIME).until(
                EC.presence_of_element_located((By.CLASS_NAME, "concordance-list"))
            )

            self.ongoing_search = True

    def __next_search_page(self):
        forward_button = (By.CSS_SELECTOR, '[aria-label="Вперед"]')

        def refresh_page():
            self.driver.refresh()
            WebDriverWait(self.driver, WAIT_TIME).until(
                EC.presence_of_element_located(forward_button)
            )
            self.__next_search_page()

        try:
            self.driver.find_element(*forward_button).click()

        except ElementClickInterceptedException:
            self.ongoing_search = False
            return

        try:
            loader_element = self.driver.find_element(By.CLASS_NAME, "results-page-loader")

            try:
                WebDriverWait(self.driver, WAIT_TIME).until(EC.staleness_of(loader_element))

            except TimeoutException:
                refresh_page()

        except NoSuchElementException:
            try:
                WebDriverWait(self.driver, WAIT_TIME).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "concordance-list"))
                )

            except TimeoutException:
                refresh_page()

    def __collect_poem_data(self) -> Iterator[PoemHtml]:
        buttons = self.driver.find_elements(By.CLASS_NAME, "result-actions__context")
        search_window = self.driver.current_window_handle

        previous_url = None

        for button in buttons:
            cur_windows = len(self.driver.window_handles)

            WebDriverWait(self.driver, WAIT_TIME).until(EC.element_to_be_clickable(button))
            button.click()

            WebDriverWait(self.driver, WAIT_TIME).until(EC.number_of_windows_to_be(cur_windows + 1))
            self.driver.switch_to.window(self.driver.window_handles[-1])

            if self.driver.current_url != previous_url:
                text_source = self.__extract_text_source()
                explain_table = self.__extract_explain_table()

                yield PoemHtml(explain_table, text_source)

            previous_url = self.driver.current_url

            self.driver.close()
            self.driver.switch_to.window(search_window)

    def __extract_text_source(self):
        text_item = (By.CLASS_NAME, "concordance-item")

        WebDriverWait(self.driver, WAIT_TIME).until(EC.presence_of_element_located(text_item))

        return self.driver.find_element(*text_item).get_attribute("innerHTML")

    def __extract_explain_table(self):
        explain_table_button = self.driver.find_element(By.XPATH, xpath["explain_table_button"])
        explain_table_button.click()

        explain_table = (By.CLASS_NAME, "explain__content")

        WebDriverWait(self.driver, WAIT_TIME).until(EC.presence_of_element_located(explain_table))

        return self.driver.find_element(*explain_table).get_attribute("innerHTML")

    def __close_onboarding(self):
        try:
            close_button = self.driver.find_element(By.XPATH, xpath["close_onboarding"])
            close_button.click()
            WebDriverWait(self.driver, WAIT_TIME).until(EC.invisibility_of_element(close_button))

        except NoSuchElementException:
            pass

    def __set_additional_features(self):
        additional_features = "(rhyme)"

        self.driver.find_element(By.XPATH, xpath["additional_features_input"]).send_keys(
            additional_features
        )
