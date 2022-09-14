import json
from scrapy.crawler import CrawlerProcess
from ScrapyTripadvisor.spiders.hotels_tripadvisor_spider import HotelsTripadvisorSpider
from ScrapyTripadvisor.spiders.restaurants_tripadvisor_spider import RestaurantsTripadvisorSpider

if __name__ == "__main__":
    data = []
    process_hotels = CrawlerProcess(
        settings={'LOG_ENABLED': False}
        )
    process_restaurants = CrawlerProcess(
        settings={'LOG_ENABLED': False}
        )
    process_hotels.crawl(HotelsTripadvisorSpider)
    process_hotels.start()
    process_restaurants.crawl(RestaurantsTripadvisorSpider)
    process_restaurants.start()