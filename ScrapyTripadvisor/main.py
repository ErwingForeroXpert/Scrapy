import json
from scrapy.crawler import CrawlerProcess
from ScrapyTripadvisor.spiders. import HotelsBookingSpider

if __name__ == "__main__":
    data = []
    process = CrawlerProcess(
        settings={'LOG_ENABLED': False}
        )
    process.crawl(HotelsBookingSpider)
    process.start()