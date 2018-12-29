# Random proxy middleware for Scrapy (http://scrapy.org/)

### Utilising Scylla to fetch operational proxies (https://github.com/imWildCat/scylla)

Processes Scrapy requests using a random proxy from list to avoid IP ban and
improve crawling speed, this plugs in to the Scylla project which provides a local database of proxies.

## Install

The Scylla project will need to be set up separately!! the quickest way is to use the docker, this will download it and run it (provided you have docker of course)

    docker run -d -p 8899:8899 -p 8081:8081 --name scylla wildcat/scylla:latest

The quick way:

    pip install scrapy-scylla-proxies

Or checkout the source and run

    python setup.py install

## settings.py

This is stuff you are going to need to integrate this middleware with scrapy.

    # Retry many times since proxies often fail
    RETRY_TIMES = 10
    # Retry on most error codes since proxies fail for different reasons
    RETRY_HTTP_CODES = [500, 503, 504, 400, 403, 404, 408]

    DOWNLOADER_MIDDLEWARES = {
        # For retries
        'scrapy.downloadermiddlewares.retry.RetryMiddleware': 290,
        # For random scylla proxies
        'scrapy_scylla_proxies.RandomProxy': 300,
        # For http proxy ip rotation
        'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 310,
    }

    # Location of the scylla server
    SCYLLA_URI = 'http://localhost:8899'
    # Proxy timeout in seconds
    PROXY_TIMEOUT = 60
    # Get only https proxies
    PROXY_HTTPS = True
