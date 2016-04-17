#!/usr/bin/env python3
import argparse
import csv
import re
import time

import pyisbn

from config import CONFIG


class Anobii2GoodReads(object):
    OUTPUT_HEADERS = ['Title', 'Author', 'Additional Authors', 'ISBN',
                      'ISBN13', 'My Rating', 'Publisher', 'Binding',
                      'Number of Pages', 'Year Published', 'Date Read',
                      'Date Added', 'Bookshelves', 'My Review',
                      'Private Notes']

    def _convert_linebreak(self, line):
        if line:
            return line.replace('\r\n', '\n').replace('\n', '<br>')
        else:
            return None

    def _convert_comment(self, title, content):
        if content:
            content = self._convert_linebreak(content)
            if title:
                print(title)
                content = '<p><b>{}</b></p>{}'.format(title.strip(), content)
            return content
        else:
            return None

    def _convert_date(self, status):
        tokens = re.split(r'[, ]+', status)
        year, month, day = None, 1, 1

        if len(tokens[-1]) == 4 and tokens[-1].isdigit():
            year = tokens[-1]
            temp = tokens[-2]
            if temp.isdigit():
                day = temp
                temp = tokens[-3]
            month = {
                'Jan': 1,
                'Feb': 2,
                'Mar': 3,
                'Apr': 4,
                'May': 5,
                'Jun': 6,
                'Jul': 7,
                'Aug': 8,
                'Sep': 9,
                'Oct': 10,
                'Nov': 11,
                'Dec': 12
            }.get(temp[:3], month)
            return '{}/{}/{}'.format(year, month, day)
        return None

    def _convert_status(self, status):
        bookshelves = []
        if status:
            date = self._convert_date(status)
            date_read, date_added = None, None
            if self.detect_strings['Not Started'] in status:
                bookshelves.append('to-read')
            elif self.detect_strings['Reading'] in status:
                bookshelves.append('currently-reading')
                date_added = date
            elif self.detect_strings['Unfinished'] in status:
                bookshelves.append('unfinished')
                date_added = date
            elif self.detect_strings['Finished'] in status:
                bookshelves.append('read')
                date_read = date
            elif self.detect_strings['Reference'] in status:
                bookshelves.append('reference')
                date_added = date
            elif self.detect_strings['Abandoned'] in status:
                bookshelves.append('abandoned')
                date_added = date

            return date_read, date_added, bookshelves
        else:
            return None, None, ['to-read']

    def convert_entry(self, entry):
        ISBN, TITLE, AUTHOR, FORMAT = 'ISBN', 'Title', 'Author', 'Format'

        NUM_OF_PAGES, PUBLISHER, PUB_DATE, PRIVATE_NOTE = 'Number of pages', 'Publisher', 'Publication date', 'Private Note'

        COMMENT_TITLE, COMMENT_CONTENT, STATUS, STARS = 'Comment title', 'Comment content', 'Status', 'Stars'

        PRIORITY = 'Priority'

        ISBN = self.headers[ISBN]
        TITLE = self.headers[TITLE]
        AUTHOR = self.headers[AUTHOR]
        FORMAT = self.headers[FORMAT]
        NUM_OF_PAGES = self.headers[NUM_OF_PAGES]
        PUBLISHER = self.headers[PUBLISHER]
        PUB_DATE = self.headers[PUB_DATE]
        PRIVATE_NOTE = self.headers[PRIVATE_NOTE]
        COMMENT_TITLE = self.headers[COMMENT_TITLE]
        COMMENT_CONTENT = self.headers[COMMENT_CONTENT]
        STATUS = self.headers[STATUS]
        STARS = self.headers[STARS]
        PRIORITY = self.headers[PRIORITY]

        title = entry.get(TITLE)

        author, additional_authors = None, None
        if AUTHOR in entry:
            all_authors = list(map(str.strip, entry[AUTHOR].split(',')))
            if len(all_authors) > 0:
                author = all_authors[0]
            if len(all_authors) > 1:
                additional_authors = ', '.join(all_authors[1:])

        isbn13 = entry.get(ISBN)
        isbn10 = None
        if isbn13:
            isbn13 = isbn13[1:-1]
            try:
                isbn10 = pyisbn.convert(isbn13)

                if len(isbn13) == 10 and len(isbn10) == 13:
                    isbn13, isbn10 = isbn10, isbn13
            except:
                # ignore inconvertible ISBNs
                pass

        publisher = entry.get(PUBLISHER)
        binding = entry.get(FORMAT)
        num_of_pages = entry.get(NUM_OF_PAGES)

        year_published = entry.get(PUB_DATE)
        if year_published:
            year_published = year_published[1:-1]

        private_notes = self._convert_linebreak(entry.get(PRIVATE_NOTE))

        # wishlist
        if PRIORITY in entry:
            bookshelves = ['to-read']
            my_rating, my_review, date_read, date_added = None, None, None, None
        # bookshelve
        else:
            my_rating = entry.get(STARS)
            my_review = self._convert_comment(
                entry.get(COMMENT_TITLE), entry.get(COMMENT_CONTENT))
            date_read, date_added, bookshelves = self._convert_status(
                entry.get(STATUS))

        if self.only_isbn:
            title = ''
            author = ''
            additional_authors = ''
            publisher = ''
            binding = ''
            num_of_pages = ''
            year_published = ''

        return (title, author, additional_authors, isbn10, isbn13, my_rating,
                publisher, binding, num_of_pages, year_published, date_read,
                date_added, ','.join(bookshelves), my_review, private_notes)

    def __init__(self, *, detect_strings, headers, only_isbn):
        self.detect_strings = detect_strings
        self.headers = headers
        self.only_isbn = only_isbn


def parse_args():
    parser = argparse.ArgumentParser(
        description='Convert aNobii csv to GoodReads csv.')
    # parser.add_argument('-w', dest='wishlist', action='store_true',
    #                     help='Process a wish list.')
    parser.add_argument('-l',
                        dest='lang',
                        default=CONFIG['default_lang'],
                        help='Input language.')
    parser.add_argument('-o',
                        '--only-isbn',
                        action='store_true',
                        help='Use only ISBN.')
    parser.add_argument('input_file',
                        metavar='anobii_csv',
                        help='aNobii CSV file')
    parser.add_argument('output_file',
                        metavar='goodreads_csv',
                        help='GreedReads CSV file export path')
    return parser.parse_args()


def main():
    args = parse_args()

    with open(args.input_file, newline='') as anobii_csv, open(args.output_file, 'w', newline='') as goodread_csv:
        anobii_reader = csv.DictReader(anobii_csv)
        goodreads_writer = csv.writer(goodread_csv)
        a2g = Anobii2GoodReads(
            detect_strings=CONFIG['detect_strings'][args.lang],
            headers=CONFIG['headers'][args.lang],
            only_isbn=args.only_isbn)

        not_convertable = []
        goodreads_writer.writerow(a2g.OUTPUT_HEADERS)
        for entry in anobii_reader:
            isbn13 = entry.get('ISBN')
            if not isbn13:
                not_convertable.append(entry)
                if args.only_isbn:
                    continue

            goodreads_writer.writerow(a2g.convert_entry(entry))

        print('Conversion done.')
        if len(not_convertable) > 0:
            print('{} entries not convertable.'.format(len(not_convertable)))
            for entry in not_convertable:
                print('{} by {}'.format(entry['Title'], entry['Author']))


if __name__ == '__main__':
    main()
