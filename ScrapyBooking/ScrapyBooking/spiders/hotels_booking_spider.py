import json
import pickle
import os
import time
import scrapy
import pandas as pd
from alive_progress import alive_bar
from scrapy import signals
from ScrapyBooking import constants as const, utils
from ScrapyBooking.items import BookingHotel
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

class HotelsBookingSpider(scrapy.Spider):

    name = "hotels_booking"
    url_home = const.LINK_RIOACHA_SEARCH
    margin_months = ["", ""] #yyyy-mm
    margin_days = ["", ""] #dd
    adults = 2
    childrens = 0
    rooms = 1 
    hotel_find = "Rioacha"

    def __init__(self, name=None, chromeOptions = webdriver.ChromeOptions(), **kwargs):

        super().__init__(name, **kwargs)
        self.data = []
        self.driver = webdriver.Chrome(
            executable_path=ChromeDriverManager().install(), options=chromeOptions)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(HotelsBookingSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def replace_properties_link(self) -> None:
        properties = {
            "<<CHECKIN_MONTHDAY>>": self.margin_days[0],
            "<<CHECKOUT_MONTHDAY>>": self.margin_days[1],
            "<<CHECKIN_YEARMONTH>>": self.margin_months[0],
            "<<CHECKOUT_YEARMONTH>>": self.margin_months[1],
            "<<GROUP_ADULTS>>": self.adults,
            "<<GROUP_CHILDREN>>": self.childrens,
            "<<ROOMS>>": self.rooms,
        }
        for key, value in properties.items():
            self.url_home = self.url_home.replace(key, str(value))

    def start_requests(self):
        use_cache = True

        if use_cache is False:
            self.replace_properties_link()
            self.driver.get(self.url_home)

        #hotels url
        hotels_url = self.get_hotel_urls(self.driver, use_cache=use_cache)
        with alive_bar(len(hotels_url), bar="filling", title="Hotels", force_tty=True) as bar:
            for url in hotels_url:
                bar()
                yield scrapy.Request(url, callback=self.parse)

    def spider_closed(self, spider):

        #save to json
        with open('hotels.json', 'w', encoding='utf8') as outfile:
            json.dump(self.data, outfile, ensure_ascii=False, indent=4)

        #save to csv
        pd.DataFrame.from_dict(self.data).to_csv("hotels.csv", encoding="utf-8-sig", index=False)

    def get_hotel_urls(self, driver: ChromeDriverManager, use_cache: bool = False) -> list:
        hotels_url = []

        if use_cache is True:
            if os.path.exists('hotels_url.pkl'):
                with open('hotels_url.pkl', 'rb') as handle:
                    hotels_url = pickle.load(handle)
            else:
                hotels_url = self.get_hotel_urls(driver)
        else:
            valid_page = True
            while valid_page is True:
                utils.wait_element_is_interactable(driver.find_element_by_xpath("//div[@class='a1b3f50dcd f7c6687c3d a1f3ecff04 f996d8c258']"))
                hotels_url.extend([x.get_attribute('href') for x in driver.find_elements_by_xpath("//div[@class='a1b3f50dcd f7c6687c3d a1f3ecff04 f996d8c258']//h3[@class='a4225678b2']/a")])

                if len(driver.find_elements_by_xpath("//button[contains(@aria-label, 'Página siguiente')]")) > 0:
                    valid_page = utils.elementIsVisible(driver, "//button[contains(@aria-label, 'Página siguiente')]",  By.XPATH) and driver.find_element_by_xpath("//button[contains(@aria-label, 'Página siguiente')]").is_enabled()
                    if valid_page is True:
                        driver.find_element_by_xpath("//button[contains(@aria-label, 'Página siguiente')]").click()
                        time.sleep(1)
                        utils.waitElementDisable(driver, "//div[contains(@class, 'a1b3f50dcd f7c6687c3d bdf0df2d01 c6ff776fac')]", By.XPATH)
                else: 
                    valid_page = False
            
            hotels_url = sorted(set(hotels_url))

            if os.path.exists('hotels_url.pkl'):
                os.remove('hotels_url.pkl')

            with open('hotels_url.pkl', 'wb') as handle:
                pickle.dump(hotels_url, handle, protocol=pickle.HIGHEST_PROTOCOL)

        return hotels_url

    def get_hotel_comments(self, url: str, **kwargs) -> None:
        comments = []
        self.driver.get(url)
        button = None if len(v:=self.driver.find_elements_by_xpath("//button[@rel='reviews' and @href='#blockdisplay4']")) == 0 else v[0]

        if button is not None:
            button.click()
            utils.waitElement(self.driver, "//input[contains(@type, 'search')]",  By.XPATH, True)
            
            valid_page = True
            while valid_page is True:
                utils.wait_element_is_interactable(self.driver, "//div[@class='c-review-block']", By.XPATH)
                elements_comments = None if len(v:=self.driver.find_elements_by_xpath("//div[@class='c-review-block']")) == 0 else v

                for element in elements_comments:
                    comment = {}
                    comment["user_name"] = "" if len(v:=element.find_elements_by_xpath(".//span[@class='bui-avatar-block__title']")) \
                        == 0 else utils.filter_empty_string(v[0].text)
                    comment["date"] = "" if len(v:=element.find_elements_by_xpath(".//div[@class='c-review-block__row']//span[@class='c-review-block__date']")) \
                        == 0 else utils.filter_empty_string(v[0].text)

                    posible_descriptions = None if len(v:=element.find_elements_by_xpath(".//div[@class='c-review']//div")) == 0 else v 
                    comment["bad_description"], comment["good_description"] = "", ""

                    if posible_descriptions is not None:
                        for description in posible_descriptions:
                            if "lalala" in description.get_attribute("class"):
                                comment["bad_description"] = "" if len(v:=description.find_elements_by_xpath(".//span[@class='c-review__body']")) == 0 else utils.filter_empty_string(v[0].text)
                            else:
                                comment["good_description"] = "" if len(v:=description.find_elements_by_xpath(".//span[@class='c-review__body']")) == 0 else utils.filter_empty_string(v[0].text)

                    comment["score"] = "" if (v:=element.find_element_by_xpath(".//div[@class='bui-grid']//div[contains(@aria-label, 'Puntuación:')]").text) is None else utils.filter_empty_string(v)
                    comments.append(comment)

                if len(self.driver.find_elements_by_xpath("//a[@class='pagenext']")) > 0:
                    valid_page = utils.elementIsVisible(self.driver, "//a[@class='pagenext']",  By.XPATH) and self.driver.find_element_by_xpath("//a[@class='pagenext']").is_enabled()
                    if valid_page is True:
                        self.driver.find_element_by_xpath("//a[@class='pagenext']").click()
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

    def parse(self, response, **kwargs):
        
        hotel = BookingHotel()

        hotel["name"] = self.extract_text(response, "//h2[@id='hp_hotel_name']/text()", skip=1)
        hotel["address"] = self.extract_text(response, "//span[contains(@class, 'hp_address_subtitle')]/text()")
        hotel["description"] = self.extract_text(response, "//div[@id='property_description_content']//p/text()")
        hotel["distance_to_beach"] = self.extract_text(response, "//div[@data-testid='DestinationCard']//span[@class='a51f4b5adb']/text()")
        hotel["categories"] = {}
        hotel["hotel_surroundings"] = {}

        parent_categories = None if len(v:=response.xpath("//ul[contains(@class, 'v2_review-scores__subscore__inner')]")) == 0 else v[0] #get first element

        if parent_categories is not None:
            categories = parent_categories.xpath(".//li//span[@class='c-score-bar__title']//text()").extract()
            scores = parent_categories.xpath(".//li//span[@class='c-score-bar__score']//text()").extract()
            if len(categories) > 0 and len(scores) > 0:
                for category, score in zip(categories, scores):
                    category, score = category.strip(), score.strip()
                    hotel["categories"][f"{category}"] = score
            else:
                print("no categories found")

        hotel_surroundings_parent = None if len(v:=response.xpath("//div[@class='hp_location_block__content_container']")) == 0 else v[0] #get first element

        if hotel_surroundings_parent is not None:

            hotel_sections = None if len(v:=hotel_surroundings_parent.xpath(".//div[contains(@class, 'hp_location_block__section_container')]")) == 0 else v

            if hotel_sections is not None:
                for section in hotel_sections:
                    if "bui-title__text" in " ".join(section.xpath(".//div[contains(@class, 'bui-title')]//@class").extract()):
                        category_name = utils.filter_empty_string(section.xpath(".//div[contains(@class, 'bui-title')]//span[contains(@class, 'bui-title__text')]//text()").extract())
                        hotel["hotel_surroundings"][f"{category_name}"] = {}
                        subcategories = None if len(v:=section.xpath(".//li[@class='bui-list__item']")) == 0 else v
                        if subcategories is not None:
                            for category in subcategories:
                                sub_cat = utils.filter_empty_string("".join(category.xpath(".//div[contains(@class, 'bui-list__description')]//text()").extract()))
                                metric = utils.filter_empty_string("".join(category.xpath(".//div[contains(@class, 'bui-list__item-action')]//text()").extract()))
                                hotel["hotel_surroundings"][f"{category_name}"][f"{sub_cat}"] = metric


        hotel["services_it_provides"] = utils.filter_empty_string(response.xpath("//div[@class='hotel-facilities__list']//div[contains(@class, 'bui-list__description')]/text()").extract())
        hotel["comments"] = self.get_hotel_comments(response.request.url)
        hotel["url"] = response.request.url

        self.data.append(hotel._values) #save data

        yield hotel