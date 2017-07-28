# -*- coding: utf-8 -*-
import json

from urllib.parse import urlparse, parse_qs

import scrapy
import diskcache as dc

from scrapy.http import FormRequest

from anobiicrawl.items import ProgressItem


class ProgressSpider(scrapy.Spider):
    name = 'progress'
    allowed_domains = ['anobii.com']

    bookshelf_url = 'http://www.anobii.com/book_shelf_public_ajax?personId={user}'
    book_progress_url = 'http://www.anobii.com/anobiireload/c3/personal_book_reading/{item_id}/en'
    login_page = 'http://www.anobii.com/login'
    book_priority = 20

    def __init__(self, visited, user, login_path, *args, **kwargs):
        super(ProgressSpider, self).__init__(*args, **kwargs)
        self.visited = dc.Cache(visited)
        self.user = user
        self.start_urls = [ProgressSpider.bookshelf_url.format(user=user)]

        self.login_path = login_path

    def start_requests(self):
        yield scrapy.Request(url=ProgressSpider.login_page,
                             callback=self.login)

    def check_login(self, response):
        for url in self.start_urls:
            yield self.make_requests_from_url(url)

    def login(self, response):
        with open(self.login_path, encoding='utf8') as f:
            login_data = json.load(f)
        yield FormRequest.from_response(response,
                                        formdata=login_data,
                                        formid='login-nav',
                                        callback=self.check_login)

    def parse_progress(self, response):
        progress = json.loads(response.body_as_unicode())
        isbn13 = response.meta['isbn13']
        title = response.meta['title']

        self.logger.warning('process item: %s: %s', isbn13, title)
        item = ProgressItem(title=title, isbn13=isbn13, progress=progress)
        yield item
        self.visited[item['isbn13']] = ''

    def parse_book(self, response):
        item_id = response.xpath(
            '//input[@class="item_id"]/@value').extract_first()
        isbn13 = response.meta['isbn13']
        title = response.meta['title']
        self.logger.warning('process edit: %s / %s / %s', item_id, isbn13,
                            title)
        if item_id:
            url = ProgressSpider.book_progress_url.format(item_id=item_id)
            yield scrapy.Request(url,
                                 self.parse_progress,
                                 priority=ProgressSpider.book_priority,
                                 meta={'isbn13': isbn13,
                                       'title': title})

    def parse(self, response):
        for tr in response.xpath('//table//tr[@class="item"]'):
            item_id_encrypted = tr.xpath('@id').extract_first()
            book_url = tr.xpath('.//a/@href').extract_first()
            book_url_tokens = book_url.split('/')
            isbn13 = book_url_tokens[-3]
            title = book_url_tokens[-4]
            self.logger.warning('%s: %s / %s', item_id_encrypted, isbn13,
                                title)

            if isbn13 not in self.visited and isbn13:
                url = response.urljoin(book_url)
                yield scrapy.Request(url,
                                     self.parse_book,
                                     priority=ProgressSpider.book_priority,
                                     meta={'isbn13': isbn13,
                                           'title': title})

        next_page_url = response.xpath(
            '//p[contains(@class, "pagination_wrap")]//a[contains(@class, "next")]/@href')
        if next_page_url:
            next_url = response.urljoin(next_page_url.extract_first())
            next_page = parse_qs(urlparse(next_url).query)['page'][0]
            url = ProgressSpider.bookshelf_url.format(
                user=self.user) + '&page={}'.format(next_page)
            self.logger.warning('turn to next page: %s', url)
            yield scrapy.Request(url, self.parse)
