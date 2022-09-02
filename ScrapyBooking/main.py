import json
from scrapy.crawler import CrawlerProcess
from ScrapyBooking.spiders.hotels_booking_spider import HotelsBookingSpider

if __name__ == "__main__":
    data = []
    process = CrawlerProcess(
        settings={'LOG_ENABLED': False}
        )
    process.crawl(HotelsBookingSpider)
    process.start()
            
    print("")