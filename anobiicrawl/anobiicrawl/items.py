# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class ProgressItem(scrapy.Item):
    title = scrapy.Field()
    isbn13 = scrapy.Field()
    progress = scrapy.Field()
