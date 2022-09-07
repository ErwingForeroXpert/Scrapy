import json
from scrapy.crawler import CrawlerProcess
from ScrapyTripadvisor.spiders.hotels_tripadvisor_spider import HotelsTripadvisorSpider
from ScrapyTripadvisor.spiders.restaurants_tripadvisor_spider import RestaurantsTripadvisorSpider

if __name__ == "__main__":
    data = []
    process = CrawlerProcess(
        settings={'LOG_ENABLED': False}
        )
    process.crawl(HotelsTripadvisorSpider)
    process.crawl(RestaurantsTripadvisorSpider)
    process.start()