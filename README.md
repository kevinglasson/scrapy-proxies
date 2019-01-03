# Random proxy middleware for [Scrapy](http://scrapy.org/)

### Using [Scylla](https://github.com/imWildCat/scylla) to fetch valid proxies.

<hr>

NOTE: I am not a 'real' programmer, help always appreciated! But it works! ... for now.

Processes Scrapy requests using a random proxies to avoid IP ban and
improve crawling speed, this plugs in to the Scylla project which provides a local database of proxies.

## Install & run Scylla

The Scylla project will need to be set-up separately!! The quickest way to do this is to use the docker container. The following command will download and run Scylla (provided you have docker installed of course).

    docker run -d -p 8899:8899 -p 8081:8081 --name scylla wildcat/scylla:latest

## Install scrapy-scylla-proxies

The quick way:

    pip install scrapy-scylla-proxies

Or checkout the source and run

    python setup.py install

## What to put in Scrapy's 'settings.py'

This is stuff you are going to need to integrate this middleware with Scrapy.

**SSP_ENABLED** - This **MUST** be set to True.

**SSP_SCYLLA_URI** - The location of the Scylla API (Default: 'http://localhost:8899').

**SSP_PROXY_TIMEOUT** - How often the proxy list is refreshed (Default: 60s).

**SSP_HTTPS** - Whether to only use HTTPS proxies, You will need this set to True if you are scraping an HTTPS site (Default: True).

### Example 'settings.py'

This is a sample taken directly from a working scraper of mine, I used it to scrape approximately 15000 items from a website without any 'bans'.

    # Configure maximum concurrent requests performed by Scrapy (default: 16)
    CONCURRENT_REQUESTS = 32

    # Enable or disable downloader middlewares
    # See https://doc.scrapy.org/en/latest/topics/downloader-middleware.html
    DOWNLOADER_MIDDLEWARES = {
        # For retries
        'scrapy.downloadermiddlewares.retry.RetryMiddleware': 290,
        # For random scylla proxies
        'scrapy_scylla_proxies.random_proxy.RandomProxyMiddleware': 300,
        # For http proxy ip rotation
        'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 310,
    }

    DOWNLOAD_TIMEOUT = 180
    RETRY_TIMES = 10
    RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 400, 429, 403, 404]

    # scrapy-scylla-proxies settings
    # Enabled
    SSP_ENABLED = True
    # Location of the scylla server
    SSP_SCYLLA_URI = 'http://localhost:8899'
    # Proxy timeout in seconds
    SSP_PROXY_TIMEOUT = 60
    # Get only https proxies
    SSP_HTTPS = True

## Tips

I also find that rotating your user agent in _combination_ with this middleware can be helpful in minimising failures due to being banned!

## Donate

If you like this middleware or it was helpful to you, you can always send me a small donation, even just a token amount. It will encourage me to keep developing this middleware and improving it! :::fire:::

[Donate here!](https://www.paypal.me/kevinglasson)
