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
from ScrapyTripadvisor.items import TripadvisorHotel
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

class HotelsTripadvisorSpider(scrapy.Spider):

    name: str = "hotels_tripadvisor"
    base_url: str = const.LINK_RIOACHA_HOTELS
    hotel_find: str = "Rioacha"

    def __init__(self, name = None, chromeOptions = webdriver.ChromeOptions(), use_cache = False, **kwargs):

        super().__init__(name, **kwargs)
        self.use_cache = use_cache
        self.data = []
        self.driver = webdriver.Chrome(
            executable_path=ChromeDriverManager().install(), options=chromeOptions)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(HotelsTripadvisorSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def start_requests(self):

        if self.use_cache is False:
            self.driver.get(self.base_url)

        #hotels url
        hotels_url = self.get_hotel_urls(self.driver, use_cache = self.use_cache)
        with alive_bar(len(hotels_url), bar="filling", title="Hotels", force_tty=True) as bar:
            for url in hotels_url:
                bar()
                yield scrapy.Request(url, callback=self.parse)

    def spider_closed(self, spider):

        #save to json
        with open(f'{self.name}.json', 'w', encoding='utf8') as outfile:
            json.dump(self.data, outfile, ensure_ascii=False, indent=4)

        #save to csv
        pd.DataFrame.from_dict(self.data).to_csv(f"{self.name}.csv", encoding="utf-8-sig", index=False)

    def get_hotel_urls(self, driver: ChromeDriverManager, use_cache: bool = False) -> list:
        hotels_url = []

        if use_cache is True:
            if os.path.exists(f'{self.name}_url.pkl'):
                with open(f'{self.name}_url.pkl', 'rb') as handle:
                    hotels_url = pickle.load(handle)
            else:
                hotels_url = self.get_hotel_urls(driver)
        else:
            valid_page = True
            utils.wait_element_is_interactable(driver, "//button[@class='rmyCe _G B- z _S c Wc wSSLS pexOo sOtnj']", By.XPATH)
            driver.find_element("xpath", "//button[@class='rmyCe _G B- z _S c Wc wSSLS pexOo sOtnj']").click()

            while valid_page is True:
                utils.wait_element_is_interactable(driver, "//div[@id='taplc_hsx_hotel_list_lite_dusty_hotels_combined_sponsored_ad_density_control_0']", By.XPATH)
                hotels_url.extend([x.get_attribute('href') for x in driver.find_elements("xpath", "//div[@class='listing_title']/a")])

                if len(driver.find_elements("xpath", "//a[contains(text(), 'Siguiente')]")) > 0:
                    valid_page = utils.elementIsVisible(driver, "//a[contains(text(), 'Siguiente')]",  By.XPATH) and driver.find_element("xpath", "//a[contains(text(), 'Siguiente')]").is_enabled()
                    if valid_page is True:
                        driver.find_element("xpath", "//a[contains(text(), 'Siguiente')]").click()
                        time.sleep(1)
                        utils.waitElementDisable(driver, "//div[contains(@class, 'loadingBox')]", By.XPATH)
                else: 
                    valid_page = False
            
            hotels_url = sorted(set(hotels_url))

            if os.path.exists(f'{self.name}_url.pkl'):
                os.remove(f'{self.name}_url.pkl')

            with open(f'{self.name}_url.pkl', 'wb') as handle:
                pickle.dump(hotels_url, handle, protocol = pickle.HIGHEST_PROTOCOL)

        return hotels_url

    def get_hotel_comments(self, **kwargs) -> None:

        comments = []        
        valid_page = True

        while valid_page is True:
            utils.wait_element_is_interactable(self.driver, "//div[@class='YibKl MC R2 Gi z Z BB pBbQr']", By.XPATH)
            elements_comments = [] if len(v:=self.driver.find_elements("xpath", "//div[@class='YibKl MC R2 Gi z Z BB pBbQr']")) == 0 else v

            for element in elements_comments:
                comment = {}
                comment["user_name"] = "" if len(v:=element.find_elements("xpath", ".//a[@class='ui_header_link uyyBf']")) \
                    == 0 else utils.filter_empty_string(v[0].text)
                comment["date"] = "" if len(v:=element.find_elements("xpath", ".//div[@class='cRVSd']//span")) \
                    == 0 else utils.filter_empty_string(self.extract_comment_date(v[0].text))

                comment["description"] = "" if len(v:=element.find_elements("xpath", ".//q[@class='QewHA H4 _a']//span")) == 0 else utils.filter_empty_string(v[0].text)

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
            match = re.search(r'(?:\()(\w{2,3})(?:.*de.*?)(\d{4})', text)

            if match != None:
                eng_month = utils.transform_month_esp2eng(match.group(1))
                return datetime.strptime(f"01-{eng_month}-{match.group(2)}", '%d-%b-%Y').strftime('%m/%Y')
        except:
          print(f'date not found {text}')
        
        
        return ""

    def parse(self, response, **kwargs):
        
        hotel = TripadvisorHotel()

        hotel["name"] = self.extract_text(response, "//h1[@id='HEADING']/text()")
        hotel["address"] = self.extract_text(response, "//span[@class='fHvkI PTrfg']/text()", skip=1)
        hotel["description"] = self.extract_text(response, "//div[@class='fIrGe _T'][1]//p/text()")
        hotel["categories"] = {}

        #dinamic information
        self.driver.get(response.request.url)
        utils.wait_page_load(self.driver)
        self.driver.maximize_window()

        categories = [] if len(v:=self.driver.find_elements("xpath", "//div[contains(@class, 'cRLRR')]")) == 0 else v

        for category in categories:
            hotel["categories"][f"{category.text}"] = self.extract_rating(category.find_element("xpath", ".//span[contains(@class, 'ui_bubble_rating')]").get_attribute('class'))

        hotel["services_it_provides"] = [] if len(v:=[value.text 
            for value in self.driver.find_elements("xpath", "//div[contains(@class, 'ssr-init-26f')]//div[contains(@class, 'OsCbb K')]//div[contains(@class, 'yplav f ME H3 _c')]")
            ]) == 0 else v

        hotel["hotel_surroundings"] = [] if len(v:=[value.text 
            for value in self.driver.find_elements("xpath", "//div[contains(@class, 'ui_column is-4 SdZtm f e')][3]//div[@class='sinXi']")
            ]) == 0 else v

        hotel["location"] = self.extract_location_from_url(self.driver.find_element("xpath", "//span[@data-test-target='staticMapSnapshot']/img").get_attribute('src'))
        
        #seleccionar todos los comentarios (idiomas)
        buttons = self.driver.find_elements("xpath", "//label[@for='LanguageFilter_0']")
        hotel["comments"] = []

        if len(buttons) == 1:
            buttons[0].click()
            hotel["comments"] = self.get_hotel_comments()

        hotel["url"] = response.request.url
        self.data.append(hotel._values) #save data

        yield hotel