# Random proxy middleware for [Scrapy](http://scrapy.org/)

### Using [Scylla](https://github.com/imWildCat/scylla) to fetch valid proxies.

<hr>

NOTE: I am not a real programmer, help always appreciated! But it works! ... for now.

Processes Scrapy requests using a random proxy from list to avoid IP ban and
improve crawling speed, this plugs in to the Scylla project which provides a local database of proxies.

## Install Scylla

The Scylla project will need to be set-up separately!! The quickest way to do this is to use the docker container. The following command will download and run Scylla (provided you have docker installed of course)

    docker run -d -p 8899:8899 -p 8081:8081 --name scylla wildcat/scylla:latest

## Install scrapy-scylla-proxies

The quick way:

    pip install scrapy-scylla-proxies

Or checkout the source and run

    python setup.py install

## What to put in Scrapy's 'settings.py'

This is stuff you are going to need to integrate this middleware with scrapy.

SSP_SCYLLA_URI - The location of the Scylla API (Default: 'http://localhost:8899')

SSP_PROXY_TIMEOUT - How often the proxy list is refreshed (Default: 60s)

SSP_HTTPS - Whether to only use HTTPS proxies, You will need this set to True if you are scraping an HTTPS site (Default: True)

### Example

    # Retry many times since proxies often fail
    RETRY_TIMES = 10
    # Retry on most error codes since proxies fail for different reasons
    RETRY_HTTP_CODES = [500, 503, 504, 400, 403, 404, 408]


    DOWNLOADER_MIDDLEWARES = {
        # For retries
        'scrapy.downloadermiddlewares.retry.RetryMiddleware': 290,
        # For random scylla proxies
        'scrapy_scylla_proxies.random_proxy.RandomProxyMiddleware': 300,
        # For http proxy ip rotation
        'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 310,
    }

    # Location of the scylla server
    SSP_SCYLLA_URI = 'http://localhost:8899'
    # Proxy timeout in seconds
    SSP_PROXY_TIMEOUT = 90
    # Get only https proxies
    SSP_HTTPS = True
