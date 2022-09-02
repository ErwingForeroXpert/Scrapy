# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import json
from itemadapter import ItemAdapter
from scrapy import signals


class ScrapybookingPipeline:

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        crawler.signals.connect(pipeline.open_spider, signals.spider_opened)
        crawler.signals.connect(pipeline.close_spider, signals.spider_closed)
        return pipeline

    def process_item(self, item, spider):
        self.result.append(item)
        return item
    
    def open_spider(self, spider):
        self.result = []

    def close_spider(self, spider):
        with open('result.json', 'w') as outfile:
            json.dump(self.result, outfile, ensure_ascii=False, indent=4)
