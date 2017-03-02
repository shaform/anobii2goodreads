#!/usr/bin/env python3
"""Update started dates on Goodreads."""

import argparse
import json
import logging

from urllib.parse import urljoin

import diskcache as dc
import pyisbn
import requests

from bs4 import BeautifulSoup as bs

from utils import random_wait


def parse_args():
    """Parse command line arguments for update_date."""
    parser = argparse.ArgumentParser(
        description='Update started dates on Goodreads.')
    parser.add_argument('-c',
                        '--cookie-json',
                        help='Cookie file.',
                        required=True)
    parser.add_argument('-b',
                        '--books',
                        help='Book items produced by scrapy.',
                        required=True)
    parser.add_argument('-d',
                        '--disk-cache',
                        help='Cache file to record updated items.',
                        required=True)
    parser.add_argument('--list-only',
                        action='store_true',
                        help='Only list books, do not actually add them.')
    parser.add_argument('--skip-error',
                        action='store_true',
                        help='Skip error items')
    parser.add_argument('--limit',
                        type=int,
                        help='Only update at most this number of books.')
    parser.add_argument('--wait', type=int, default=5, help='Seconds to wait.')
    return parser.parse_args()


def get_read_entries(path, disk_cache, skip_error):
    with open(path, encoding='utf8') as f:
        for l in f:
            entry = json.loads(l)
            if entry['isbn13'] in disk_cache:
                if skip_error:
                    continue
                elif disk_cache[entry['isbn13']] == '':
                    continue
            if ('progress' in entry and
                    'readingProgress' in entry['progress'] and
                    entry['progress']['readingProgress']):
                if len(entry['progress']['readingProgress']) > 0:
                    reading_progress = entry['progress']['readingProgress'][-1]
                    entry['reading_progress'] = reading_progress
                    if reading_progress.get('startaa'):
                        yield entry


def check_exists(session, isbns, cookies):
    """Check if a book exists in Goodreads

    :param session: requests session
    :param isbns: the ISBNs of the book
    :param cookies: login cookie for Goodreads
    """
    search_url = 'https://www.goodreads.com/search'
    for isbn in isbns:
        resp = session.request('get',
                               search_url,
                               params={'q': isbn},
                               cookies=cookies)
        if resp.url.startswith('https://www.goodreads.com/book/show/'):
            return resp

    return None


def get_edit_url(resp):
    """Get edit url for updating books.

    :param resp: requests response
    """
    page = bs(resp.content, 'html.parser')
    edit_links = page.find_all('a', {'class': 'actionLinkLite'})
    for edit_link in edit_links:
        url = edit_link['href']
        if url.startswith('/review/edit'):
            return urljoin(resp.url, url)
    return None


def get_form_data(session, cookies, url):
    """Get edit url for updating books.

    :param session: requests session
    :param cookies: login cookie for Goodreads
    :param url: edit url
    """
    resp = session.get(url, cookies=cookies)
    page = bs(resp.content, 'html.parser')
    form = page.find('form', {'name': 'reviewForm'})
    if form:
        form_data = {}
        action_url = urljoin(url, form['action'])
        for elem in form.find_all('input', {'name': True}):
            if elem.get('type') == 'checkbox':
                if elem.get('checked') == 'true':
                    form_data[elem['name']] = elem.get('value', '')
            else:
                form_data[elem['name']] = elem.get('value', '')
        for elem in form.find_all('textarea', {'name': True}):
            form_data[elem['name']] = elem.text
        for elem in form.find_all('select', {'name': True}):
            if elem['name'].startswith('readingSessionDatePicker'):
                opt = elem.find('option', {'class': 'setDate',
                                           'selected': True})
                if opt:
                    value = opt.get('value', opt.text)
                else:
                    value = ''
                form_data[elem['name']] = value
        return action_url, form_data

    return None, None


def update_book(entry, payload, url, session, cookies):
    """Update book.

    :param entry: the book entry
    :param payload: the payload
    :param url: the submit url
    :param session: requests session
    :param cookies: login cookie for Goodreads
    """

    for key in ('start', 'end'):
        changed = False
        previous = []
        now = []
        for range_x, range_en in (('aa', 'year'), ('mm', 'month'),
                                  ('gg', 'day')):
            num = entry['reading_progress'].get(key + range_x, '').lstrip('0')

            for name in list(payload):
                if ('readingSessionDatePicker' in name and
                    ('[' + key + ']') in name and
                    ('[' + range_en + ']') in name):
                    if payload[name]:
                        previous.append(int(payload[name]))
                    if num:
                        now.append(int(num))

                    if num:
                        if payload[name] != num:
                            if payload[name]:
                                changed = True
                            payload[name] = num
                    elif payload[name] == '':
                        del payload[name]

                    break

        if changed:
            logging.warning('%s - changing %s to %s', entry['title'],
                            '-'.join([str(n) for n in previous]),
                            '-'.join([str(n) for n in now]))
            if key == 'start' and len(previous) == 3 and len(
                    now) == 3 and now < previous:
                logging.warning('ok - choose early date')
            else:
                logging.warning('problematic - skip')
                return False

    # send request
    resp = session.post(url, payload, cookies=cookies)

    return resp.status_code == requests.codes.ok


def update_to_goodreads(entries, cookies, disk_cache, limit, wait):
    """Update book entries to Goodreads.

    :param entries: list of books
    :param cookies: login cookie for Goodreads
    :param disk_cache: cache of updated books
    """

    session = requests.Session()

    success = []
    error = []

    for entry in entries:
        isbn13 = entry['isbn13']

        isbns = [isbn13]
        try:
            isbn10 = pyisbn.convert(isbn13)
            isbns.append(isbn10)
        except Exception:
            pass

        resp = check_exists(session, (isbn10, isbn13), cookies)
        if not resp:
            logging.warning('{} couldn\'t be found'.format(repr_book(entry)))
            error.append(entry)
            disk_cache[entry['isbn13']] = 'e'
            random_wait(2)
            continue

        url = get_edit_url(resp)
        if not url:
            logging.warning('{}\' url is not found'.format(repr_book(entry)))
            error.append(entry)
            disk_cache[entry['isbn13']] = 'e'
            random_wait(2)
            continue

        submit_url, form_data = get_form_data(session, cookies, url)
        if not form_data:
            logging.warning('{}\' form data is not found'.format(repr_book(
                entry)))
            error.append(entry)
            disk_cache[entry['isbn13']] = 'e'
            random_wait(2)
            continue

        # Do not cause any updates
        form_data['review[cog_explicit]'] = '0'
        for key in ('add_to_blog', 'add_update'):
            if key in form_data:
                form_data[key] = '0'

        # sanity check
        if len([key for key in form_data if 'readingSessionDatePicker' in key
                ]) != 10:
            logging.warning('{}\' date is problematic'.format(repr_book(
                entry)))
            logging.warning(form_data)
            error.append(entry)
            disk_cache[entry['isbn13']] = 'e'
            continue

        if update_book(entry, form_data, submit_url, session, cookies):
            success.append(entry)
            disk_cache[entry['isbn13']] = ''
        else:
            error.append(entry)
            disk_cache[entry['isbn13']] = 'e'

        if limit is not None and len(success) >= limit:
            break

        random_wait()

    return success, error


def repr_date(year, month, date):
    tokens = []
    for item in (year, month, date):
        if item:
            tokens.append(item)
    return '-'.join(tokens)


def repr_book(book):
    """Get book information to print on screen."""
    start_date = repr_date(book['reading_progress'].get('startaa'),
                           book['reading_progress'].get('startmm'),
                           book['reading_progress'].get('startgg'))
    end_date = repr_date(book['reading_progress'].get('endaa'),
                         book['reading_progress'].get('endmm'),
                         book['reading_progress'].get('endgg'))
    return '{} ({}): {}~{}'.format(book['title'], book['isbn13'], start_date,
                                   end_date)


def main():
    """Parse Scrapy input and auto update them to Goodreads."""
    args = parse_args()

    disk_cache = dc.Cache(args.disk_cache)
    entries = list(get_read_entries(args.books, disk_cache, args.skip_error))

    logging.warning('== {} entries to update =='.format(len(entries)))

    with open(args.cookie_json) as cookie_file:
        cookies = json.load(cookie_file)

    if args.list_only:
        for row in entries:
            logging.warning('to update: {}'.format(repr_book(row)))
    else:
        success, error = update_to_goodreads(entries, cookies, disk_cache,
                                             args.limit, args.wait)
        if len(success) > 0:
            logging.warning('== {} files updated =='.format(len(success)))
            for row in success:
                logging.warning('updated: {}'.format(repr_book(row)))

        if len(error) > 0:
            logging.warning('== {} files error =='.format(len(error)))
            for row in error:
                logging.warning('error: {}'.format(repr_book(row)))


if __name__ == '__main__':
    main()
