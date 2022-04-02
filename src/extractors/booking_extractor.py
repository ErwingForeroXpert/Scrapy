import scrapy
import re

import sys
sys.path.append(".")

from . import utils
from src import const

class BookingExtractor(scrapy.Spider):
    name = "booking_extractor"
    start_url = const.URLS["booking"]

    def get_accommodation(self, *args):
        pass
    
    def get_accomodation_list(self, url: str) -> list[dict]:
        result = scrapy.Request(url = url)
        selector = scrapy.Selector(response = result)

        list_result = []
        elements = selector.xpath("//div[@class='d4924c9e74']//div[@data-testid='property-card']")

        for element in elements:
            div_general = element.xpath("//div[@class='ea9bf183d3 d14b211b4f febf9d5862 af9697be6b d7ff3c30ad']//div[@class='e278108e40 e04c8ab03a']")
            div_auxiliar = element.xpath("//div[@class='ea9bf183d3 d14b211b4f febf9d5862 af9697be6b d7ff3c30ad']//div[@class='ea9bf183d3 f920833fe5 a60dd8971f']")

            title = div_general.xpath("//div[@data-testid='title']/text()").extract()
            distance_of_center = div_general.xpath("//div[@data-testid='location']//span[@data-testid='distance']/text()").extract()
            distance_of_center = utils.extract_meters_and_kilometers(distance_of_center)
            
        return list_result
