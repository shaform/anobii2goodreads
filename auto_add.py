import argparse
import csv
import json
import random
import time

import requests

from bs4 import BeautifulSoup as bs


def random_wait():
    offset = random.randint(1, 5)
    time.sleep(10 + offset)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Automatically add new books to Goodreads.')
    parser.add_argument('-c',
                        '--cookie-json',
                        help='Cookie file',
                        required=True)
    parser.add_argument(
        '-a',
        '--anobii-converted-csv',
        help='aNobii CSV file converted by anobii2goodreads.py',
        required=True)
    parser.add_argument(
        '-g',
        '--goodreads-csv',
        help='GreedReads CSV export file to compare differences',
        required=True)
    return parser.parse_args()


def get_all_present_isbns(path):
    all_isbns = set()
    with open(path, newline='') as goodread_csv:
        goodreads_reader = csv.DictReader(goodread_csv)
        for r in goodreads_reader:
            for name in ('ISBN', 'ISBN13'):
                isbn = r.get(name, '').strip('="')
                if isbn != '':
                    all_isbns.add(isbn)
    return all_isbns


def get_all_missing_entries(path, all_isbns):
    entries = []
    skipped = []
    with open(path, newline='') as anobii_csv:
        anobii_reader = csv.DictReader(anobii_csv)

        for r in anobii_reader:
            # try to get ISBNS
            title = r.get('Title')
            author = r.get('Author')
            isbn10 = r.get('ISBN')
            isbn13 = r.get('ISBN13')
            publisher = r.get('Publisher')
            num_of_pages = r.get('Number of Pages')
            pub_year = pub_month = pub_day = None

            pub_date = r.get('Year Published')
            if pub_date:
                ts = pub_date.split('-')
                if len(ts) > 0 and len(ts[0]) == 4:
                    try:
                        pub_year = ts[0]
                    except:
                        pass
                if len(ts) > 1 and len(ts[1]) == 2:
                    try:
                        d = int(ts[1])
                        if 1 <= d <= 12:
                            pub_month = str(d)
                    except:
                        pass
                if len(ts) > 2 and len(ts[2]) == 2:
                    try:
                        d = int(ts[2])
                        if 1 <= d <= 31:
                            pub_day = str(d)
                    except:
                        pass

            entry = (title, author, isbn10, isbn13, publisher, num_of_pages,
                     pub_year, pub_month, pub_day)

            correct_isbns = isbn13 and len(isbn13) == 13 and isbn10 and len(
                isbn10) == 10
            required_data = title and author
            if not correct_isbns or not required_data:
                skipped.append(entry)
            elif isbn10 not in all_isbns and isbn13 not in all_isbns:
                entries.append(entry)

    return entries, skipped


def add_to_goodreads(entries, cookies):
    url = 'https://www.goodreads.com/book/new'

    success = []
    duplicate = []

    for entry in entries:
        (title, author, isbn10, isbn13, publisher, num_of_pages, pub_year,
         pub_month, pub_day) = entry

        # obtain authenticity_token
        req = requests.request('get', url, cookies=cookies)
        page = bs(req.content)
        book_form = page.find('form', {'id': 'bookForm'})
        authenticity_token = book_form.find(
            'input', {'name': 'authenticity_token'})['value']

        # construct payload

        payload = {'utf8': '✓',
                   'authenticity_token': authenticity_token,
                   'book[title]': title,
                   'book[sort_by_title]': title,
                   'author[name]': author,
                   'book[isbn]': isbn10,
                   'book[isbn13]': isbn13}

        if publisher:
            payload['book[publisher]'] = publisher

        if num_of_pages:
            payload['book[num_pages]'] = num_of_pages

        if pub_year:
            payload['book[publication_year]'] = pub_year

        if pub_month:
            payload['book[publication_month]'] = pub_month

        if pub_day:
            payload['book[publication_day]]'] = pub_day

        print(payload)

        # send request
        req = requests.post(url, payload, cookies=cookies)

        # check result
        page = bs(req.content)
        link = page.find('a', {'class': 'bookTitle'})
        if link is not None:
            link = 'https://www.goodreads.com{}'.format(link['href'])
            print('success: '.format(link))
            success.append(entry)
        else:
            if 'is taken by an existing book' in page.text:
                print('duplicate')
                duplicate.append(entry)
            else:
                print('== error: stop processing to prevent bad things ==')
                break

        random_wait()

    return success, duplicate


def main():
    args = parse_args()

    all_isbns = get_all_present_isbns(args.goodreads_csv)

    entries, skipped = get_all_missing_entries(args.anobii_converted_csv,
                                               all_isbns=all_isbns)
    print('== {} entries to add =='.format(len(entries)))

    with open(args.cookie_json) as f:
        cookies = json.load(f)

    success, duplicate = add_to_goodreads(entries, cookies)

    if len(success) > 0:
        print('== {} files added =='.format(len(success)))
        for r in success:
            print('added: {} by {} ({}/{})'.format(r[0], r[1], r[2], r[3]))

    if len(duplicate) > 0:
        print('== {} files already present =='.format(len(duplicate)))
        for r in success:
            print('added: {} by {} ({}/{})'.format(r[0], r[1], r[2], r[3]))

    if len(skipped) > 0:
        print('== {} files skipped due to missing data =='.format(len(
            skipped)))
        for r in skipped:
            print('skipped: {} by {} ({}/{})'.format(r[0], r[1], r[2], r[3]))


if __name__ == '__main__':
    main()
