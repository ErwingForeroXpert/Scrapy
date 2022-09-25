from datetime import datetime
import json
import pickle
import os
import re
import time
import scrapy
import pandas as pd
from alive_progress import alive_bar
from scrapy import signals
from ScrapyTripadvisor import constants as const, utils
from ScrapyTripadvisor.items import TripAdvisorRestaurant

from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

class RestaurantsTripadvisorSpider(scrapy.Spider):

    name: str = "restaurants_tripadvisor"
    base_url: str = const.LINK_RIOACHA_RESTAURANTS

    def __init__(self, name = None, chromeOptions = webdriver.ChromeOptions(), use_cache = False, **kwargs):

        super().__init__(name, **kwargs)
        self.use_cache = use_cache
        self.data = []
        self.driver = webdriver.Chrome(
            executable_path=ChromeDriverManager().install(), options=chromeOptions)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(RestaurantsTripadvisorSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def start_requests(self):

        self.driver.get(self.base_url)

        #restaurants url
        restaurants_url = self.get_urls(self.driver, use_cache = self.use_cache)
        with alive_bar(len(restaurants_url), bar="filling", title="Restaurants", force_tty=True) as bar:
            for url in restaurants_url:
                bar()
                yield scrapy.Request(url, callback=self.parse)

    def spider_closed(self, spider):

        #save to json
        with open(f'{self.name}.json', 'w', encoding='utf8') as outfile:
            json.dump(self.data, outfile, ensure_ascii=False, indent=4)

        #save to csv
        pd.DataFrame.from_dict(self.data).to_csv(f"{self.name}.csv", encoding="utf-8-sig", index=False)

    def get_urls(self, driver: ChromeDriverManager, use_cache: bool = False) -> list:
        urls = []

        if use_cache is True:
            if os.path.exists(f'{self.name}.pkl'):
                with open(f'{self.name}.pkl', 'rb') as handle:
                    urls = pickle.load(handle)
            else:
                urls = self.get_urls(driver)
        else:
            valid_page = True

            while valid_page is True:
                utils.wait_element_is_interactable(driver, "//div[@class='zdCeB Vt o']", By.XPATH)
                urls.extend([x.get_attribute('href') for x in driver.find_elements("xpath", "//a[@class='Lwqic Cj b']")])

                if len(driver.find_elements("xpath", "//a[contains(text(), 'Siguiente')]")) > 0:
                    valid_page = utils.elementIsVisible(driver, "//a[contains(text(), 'Siguiente')]",  By.XPATH) and driver.find_element("xpath", "//a[contains(text(), 'Siguiente')]").is_enabled()
                    if valid_page is True:
                        driver.find_element("xpath", "//a[contains(text(), 'Siguiente')]").click()
                        time.sleep(1)
                        utils.waitElementDisable(driver, "//div[contains(@class, 'loadingBox')]", By.XPATH)
                else: 
                    valid_page = False
            
            urls = sorted(set(urls))

            if os.path.exists(f'{self.name}.pkl'):
                os.remove(f'{self.name}.pkl')

            with open(f'{self.name}.pkl', 'wb') as handle:
                pickle.dump(urls, handle, protocol = pickle.HIGHEST_PROTOCOL)

        return urls

    def get_comments(self, **kwargs) -> None:

        comments = []        
        valid_page = True

        while valid_page is True:
            utils.wait_element_is_interactable(self.driver, "//div[@class='review-container']", By.XPATH)
            elements_comments = [] if len(v:=self.driver.find_elements("xpath", "//div[@class='review-container']")) == 0 else v

            for element in elements_comments:
                comment = {}
                comment["user_name"] = "" if len(v:=element.find_elements("xpath", ".//div[@class='info_text pointer_cursor']")) \
                    == 0 else utils.filter_empty_string(v[0].text)
                comment["date"] = "" if len(v:=element.find_elements("xpath", ".//div[@class='prw_rup prw_reviews_stay_date_hsx']")) \
                    == 0 else utils.filter_empty_string(self.extract_comment_date(v[0].text.replace("Fecha de la visita:", "")))

                comment["description"] = "" if len(v:=element.find_elements("xpath", ".//div[@class='entry']//p[@class='partial_entry']")) == 0 else utils.filter_empty_string(v[0].text)

                comment["score"] = "" if len(v:=element.find_elements("xpath", ".//span[contains(@class, 'ui_bubble_rating')]")) == 0 else self.extract_rating(v[0].get_attribute('class'))
                comments.append(comment)

            if len(self.driver.find_elements("xpath", "//a[@class='ui_button nav next primary ']")) > 0:
                valid_page = utils.elementIsVisible(self.driver, "//a[@class='ui_button nav next primary ']",  By.XPATH) and self.driver.find_element("xpath", "//a[@class='ui_button nav next primary ']").is_enabled()
                if valid_page is True:
                    self.driver.find_element("xpath", "//a[@class='ui_button nav next primary ']").click()
                    time.sleep(1)
            else: 
                valid_page = False

        return comments

    def extract_if_exist(self, response: 'scrapy.Request', xpath: str) -> 'Any':
        try:
            return response.xpath(xpath).extract()
        except Exception as e:
            print(f"empty field or not found {e}")
            return None

    def extract_text(self, response: 'scrapy.Request', xpath: str, skip: int = 0) -> str:
        try:
            result = self.extract_if_exist(response, xpath)
            if result is not None:
                text_extracted = ""
                if utils.isIterable(result):
                    for idx, res in enumerate(result):
                        if idx >= skip:
                            text_extracted = f"{text_extracted} {res}".strip()
                else:   
                    text_extracted = str(result)
                return text_extracted
            else:   
                return ""
        except Exception as e:
            print(f"invalid extraction of string, {e}")
            return ""

    def extract_location_from_url(self, url: str) -> str:
        if url != "":
            sections = url.split("&")
            for section in sections:
                if "center" in section:
                    location_found = re.search(r"(\-?\d{1,2}\.\d+).*\,(\-?\d{1,3}\.\d+)", section) #valid latitude and longitude
                    if location_found is not None:
                        return location_found.group(0)

        return ""

    def extract_rating(self, text: str) -> str:
        if text != "":
            rating = re.search(r"\d+", text) 
            if rating is not None:
                rating = rating.group(0)
                return f"{rating[0]},{rating[-1]}" if len(rating) == 2 else rating

        return ""

    def extract_comment_date(self, text: str) -> str:

        try:
            match = re.search(r'(\w+)(?:.*de.*?)(\d{4})', text)

            if match != None:
                eng_month = utils.transform_month_esp2eng(match.group(1))
                return datetime.strptime(f"01-{eng_month}-{match.group(2)}", '%d-%b-%Y').strftime('%m/%Y')
        except:
          print(f'date not found {text}')
        
        
        return ""

    def parse(self, response, **kwargs):
        
        hotel = TripAdvisorRestaurant()

        hotel["name"] = self.extract_text(response, "//h1[@data-test-target='top-info-header']/text()")
        hotel["address"] = self.extract_text(response, "//a[@class='AYHFM' and @href='#MAPVIEW']/text()")
        hotel["categories"] = {}

        #dinamic information
        self.driver.get(response.request.url)
        utils.wait_page_load(self.driver)
        self.driver.maximize_window()
        
        categories = [] if len(v:=self.driver.find_elements("xpath", "//div[contains(@class, 'DzMcu')]")) == 0 else v

        for category in categories:
            hotel["categories"][f"{category.text}"] = self.extract_rating(category.find_element("xpath", ".//span[contains(@class, 'ui_bubble_rating')]").get_attribute('class'))

        details = v if len(v:=self.driver.find_elements("xpath", "//div[@class='BMlpu']/div")) >= 1 else []
        hotel["types_of_food"] = []

        for detail in details:
            _types = detail.find_elements("xpath", ".//div[@class='tbUiL b']")
            posible_title = _types[0].text.lower() if len(_types) > 0 else ""
            if posible_title == "tipos de comida":
                hotel["types_of_food"] = v[0].text.split(",") if len(v:=detail.find_elements("xpath", ".//div[@class='SrqKb']")) > 0 else []

        hotel["location"] = self.extract_location_from_url(self.driver.find_element("xpath", "//span[@data-test-target='staticMapSnapshot']/img").get_attribute('src'))
        
        #seleccionar todos los comentarios (idiomas)
        buttons = self.driver.find_elements("xpath", "//label[@for='filters_detail_language_filterLang_ALL']")
        hotel["comments"] = []

        if len(buttons) >= 1:
            buttons[0].click()
            hotel["comments"] = self.get_comments()

        hotel["url"] = response.request.url
        self.data.append(hotel._values) #save data
        
        yield hotel