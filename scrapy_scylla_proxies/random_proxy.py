# Copyright (C) 2013 by Aivars Kalvans <aivars.kalvans@gmail.com> (Original)
# Copyright (C) 2013 by Kevin Glasson <kevinglasson+scrapyscylla@gmail.com> (Scylla Integration)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import base64
import logging
import random
import re
import threading
import urllib.parse

import requests
from scrapy import signals
from scrapy.exceptions import CloseSpider, NotConfigured

from scrapy_scylla_proxies.scylla import Scylla
from scrapy_scylla_proxies.exceptions import SSPNoProxiesError

logger = logging.getLogger('scrapy-scylla-proxies.random_proxy')


class RandomProxyMiddleware(object):
    """
    Settings:
    * ``SSP_ENABLED`` - Whether this middleware is enabled

    * ``SSP_SCYLLA_URI`` - The location of the Scylla API (Default: 'http://localhost:8899')

    * ``SSP_PROXY_TIMEOUT`` - How often the proxy list is refreshed (Default: 60s)

    * ``SSP_HTTPS`` - Whether to only use HTTPS proxies, You will need this set to True if you are scraping an HTTPS site (Default: True)
    """

    def __init__(self, scylla, timeout, https, crawler):
        # Scylla object for interaction with the proxy lists
        self.scylla = scylla
        # How often to get a new list of proxies from scylla
        self.timeout = timeout
        # HTTPS only
        self.https = https

        # The current list of proxies to choose from
        self.proxies = None
        # Keep a handle on the proxy refresh thread
        self.refresh_thread = None

        # Start the middleware i.e. perform the setup stuff.
        self._start()

    def _start(self):
        """Start the middleware."""

        # Refresh the proxies list (or populate if it's the first time)
        self._threading_proxies()

        # Exception if the list is empty for some reason. This is probably unreachable....
        if not self.proxies:
            raise SSPNoProxiesError(
                'Proxies list is empty, Wait a fee minutes for Scylla to populate.')

    @classmethod
    def from_crawler(cls, crawler):
        """Called by Scrapy to create an instance of this middleware.

        :param crawler: Current crawler
        :type crawler: Crawler object
        :raises NotConfigured: Issue with middleware settings
        :return: Instance of the middleware
        :rtype: RandomProxyMiddelware
        """

        # Get all the settings
        s = crawler.settings

        # Check if eabled
        if not s.getbool('SSP_ENABLED', default=False):
            raise NotConfigured(
                'scrapy_scylla_proxies middleware is not enabled')

        # Fetch my settings
        scylla_uri = s.get('SSP_SCYLLA_URI', default='http://localhost:8899')
        timeout = s.getint('SSP_PROXY_TIMEOUT', default=60)
        https = s.getbool('SSP_HTTPS', default=True)

        # Create a a Scylla object
        scylla = Scylla(scylla_uri)

        # Create an instance of this middleware
        mw = cls(scylla, timeout, https, crawler)

        # Connect to signals
        crawler.signals.connect(
            mw.spider_closed, signal=signals.spider_closed)

        return mw

    def _threading_proxies(self):
        """Starts a thread that will refresh the proxy list every 'timeout' seconds.

        """

        logger.info('Starting proxy refresh threading.')
        # Get the first list of proxies
        self._get_proxies()
        # Call this function again after the time elapses
        self.refresh_thread = threading.Timer(
            self.timeout, self._get_proxies)
        # Start the thread
        self.refresh_thread.start()

    def _get_proxies(self):
        """Requesting new proxies from Scylla."""

        logger.debug('Requesting new proxies from Scylla.')
        # Refresh the proxy list
        self.proxies = self.scylla.get_proxies()

    def process_request(self, request, spider):
        """Called by Scrapy for each request.

        This is the core of the middleware and allows changing of the current request. This is where a random proxy is added to the request object.

        :param request: Current request
        :type request: Request object
        :param spider: Current spider
        :type spider: Spider object
        :return: Nothing
        """

        # If a proxy is already present
        if 'proxy' in request.meta:
            # And an exception hasn't occured
            if 'exception' in request.meta:
                if request.meta["exception"] is False:
                    # Just return i.e. the middleware does nothing
                    return

        # Set the exception to False
        request.meta["exception"] = False

        # Randomly choose a proxy
        try:
            proxy = random.choice(self.proxies)
        except IndexError as e:
            raise SSPNoProxiesError(
                'Proxies list is empty, Wait a fee minutes for Scylla to populate.') from e

        # Format it!
        if self.https:
            proxy_url = 'https://{}:{}'.format(proxy['ip'], proxy['port'])
        else:
            proxy_url = 'http://{}:{}'.format(proxy['ip'], proxy['port'])

        # Set the proxy
        request.meta['proxy'] = proxy_url
        logger.debug('Using proxy: %s' % proxy_url)

    def process_exception(self, request, exception, spider):
        """Process exception while attempting to scrape a URL.

        Currently this method doesn't do anything much, in the future it could be used to alter the proxies list or something based on exceptions. However HTTP 'ERROR' don't pass through here, only real exceptions like a requests timeout.

        :param request: Current request
        :type request: Requests object
        :param exception: Current exception
        :type exception: Exception object
        :param spider: Current spider
        :type spider: Spider object
        """

        if 'proxy' not in request.meta:
            return

        # What proxy had the exception
        proxy = request.meta['proxy']

        logger.error('Exception using proxy %s. %s. %s' %
                     (proxy, exception, request))
        # Set exception to True
        request.meta["exception"] = True

    def spider_closed(self, spider, reason):
        """Called when the spider is closed

        :param spider: Spider instance
        :type spider: Scrapy Spider
        :param reason: Reason signal was sent i.e. 'finished'
        :type reason: Scrapy Signal
        """

        # Close the proxy refresh thread
        self.refresh_thread.cancel()
        logger.info('Closing')
