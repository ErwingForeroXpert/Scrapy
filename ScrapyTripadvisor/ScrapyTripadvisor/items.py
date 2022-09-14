# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class TripadvisorHotel(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    name = scrapy.Field()
    address = scrapy.Field()
    location = scrapy.Field()
    description = scrapy.Field()
    distance_to_beach = scrapy.Field()
    categories = scrapy.Field()
    hotel_surroundings = scrapy.Field()
    services_it_provides = scrapy.Field()
    comments = scrapy.Field()
    url = scrapy.Field()
