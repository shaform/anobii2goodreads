import argparse
import csv

from auto_add import get_all_present_isbns


def get_all_present_isbns_in_anobii(path):
    all_isbns = set()
    with open(path, newline='') as incsv:
        reader = csv.reader(incsv)
        # skip header
        next(reader)
        for r in reader:
            for isbn in (r[3], r[4]):
                if isbn:
                    all_isbns.add(isbn)
    return all_isbns


def main():
    args = parse_args()

    if args.reverse:
        all_isbns = get_all_present_isbns_in_anobii(args.anobii_converted_csv)

        with open(args.output,
                  'w',
                  newline='') as outcsv, open(args.goodreads_csv,
                                              newline='') as incsv:
            reader = csv.reader(incsv)

            rows = []
            for r in reader:
                if r[5].strip('="') not in all_isbns and r[6].strip(
                        '="') not in all_isbns:
                    rows.append(r)

            writer = csv.writer(outcsv)
            writer.writerows(rows)
    else:
        all_isbns = get_all_present_isbns(args.goodreads_csv)

        with open(args.output,
                  'w',
                  newline='') as outcsv, open(args.anobii_converted_csv,
                                              newline='') as incsv:
            reader = csv.reader(incsv)

            rows = []
            for r in reader:
                if r[3] not in all_isbns and r[4] not in all_isbns:
                    rows.append(r)

            writer = csv.writer(outcsv)
            writer.writerows(rows)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Filter already present books')
    parser.add_argument(
        '-a',
        '--anobii-converted-csv',
        help='aNobii CSV file converted by anobii2goodreads.py',
        required=True)
    parser.add_argument(
        '-g',
        '--goodreads-csv',
        help='Goodreads CSV export file to compare differences',
        required=True)
    parser.add_argument(
        '-r',
        '--reverse',
        action='store_true',
        help='Instead find out which books are only present in Goodreads')

    parser.add_argument('-o', '--output', help='Filterd output', required=True)
    return parser.parse_args()


if __name__ == '__main__':
    main()
