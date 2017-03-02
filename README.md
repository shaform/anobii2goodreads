anobii2goodreads
================

Another script to convert a CSV export from the Anobii website
to a CSV similar to Goodreads export, which could be imported via
the [import page](http://www.goodreads.com/review/import).

Inspired by https://github.com/tijs/Anobii2Goodreads.

Usage
=====

To convert `anobii.csv` to `anobii_converted.csv`:

    python3 anobii2goodreads/anobii2goodreads.py [-l LANG] [-o] anobii.csv anobii_converted.csv

    -o is used to clear data such as title and author to prevent Goodreads from auto-matching books that may have different ISBNs.

`anobii_converted.csv` could be used to import to Goodreads.

Sometimes, certain books may not be present in the Goodreads database. In that case, export your Goodreads bookshelf as `goodreads_exported.csv` to see what have been imported, and use `auto_add.py` to add the non-imported books:

    python3 anobii2goodreads/auto_add.py -c COOKIE_JSON -a anobii_converted.csv -g goodreads_exported.csv

You'll need your session cookie from your browser to access Goodreads from `auto_add.py`.

However, reading progress is not entirely preserved in the process. But it's still possible to obtain complete reading history by directly crawling aNobii website:

    cd anobiicrawl/
    scrapy crawl progress -a visited=CACHE_PATH_FOR_CRAWL -a user=YOUR_USER_NAME -a login_path=anobii.login.json -o anobii_progress.jl

Afterwards, we could update the reading dates for books on Goodreads:

    cd ../
    python3 anobii2goodreads/update_date.py -c COOKIE_JSON -b anobiicrawl/anobii_progress.jl -d `CACHE_PATH_FOR_UPDATE`
