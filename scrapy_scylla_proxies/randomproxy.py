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
import urllib.parse
import threading
from scrapy import signals
from scrapy.exceptions import CloseSpider, NotConfigured

import requests

log = logging.getLogger('scrapy-scylla-proxies')

SCYLLA_API_PATH = '/api/v1/proxies'
SCYLLA_STATS_PATH = '/api/v1/stats'


class RandomProxy(object):
    """
    Settings:
    * ``SSP_SCYLLA_URI`` - The location of the Scylla API (Default: 'http://localhost:8899')

    * ``SSP_PROXY_TIMEOUT`` - How often the proxy list is refreshed (Default: 60s)

    * ``SSP_HTTPS`` - Whether to only use HTTPS proxies, You will need this set to True if you are scraping an HTTPS site (Default: True)
    """

    def __init__(self, scylla, timeout, https, crawler):
        # Location of the scylla JSON api endpoint
        self.scylla = scylla
        # How often to get a new list of proxies from scylla
        self.timeout = timeout
        # HTTPS only
        self.https = https

        # The current list of proxies to choose from
        self.proxies = None
        # Keep a handle on the proxy refresh thread
        self.refresh_thread = None

        # Refresh the proxies list (or populate if it's the first time)
        self.threading_proxies()

        # Exception if the list is empty for some reason
        if self.proxies is None:
            raise ValueError('Proxies list is empty.')

    @classmethod
    def from_crawler(cls, crawler):
        """Called by scrapy to create an instance of this middleware
        
        :param crawler: crawler
        :type crawler: crawler
        :raises NotConfigured: Issue with middleware settings
        :return: Instance of the middleware
        :rtype: RandomProxy
        """

        # Get all the settings
        s = crawler.settings

        # Fetch my settings
        scylla = s.get('SSP_SCYLLA_URI', 'http://localhost:8899')
        timeout = s.get('SSP_PROXY_TIMEOUT', 60)
        https = s.get('SSP_HTTPS', True)

        if not RandomProxy.scylla_alive_and_populated(scylla):
            raise NotConfigured(
                'Scylla is reachable but the proxy list is empty.')

        # Create an instance of this middleware
        mw = cls(scylla, timeout, https, crawler)

        # Connect to signals
        crawler.signals.connect(
            mw.spider_closed, signal=signals.spider_closed)

        return mw

    @staticmethod
    def scylla_alive_and_populated(scylla):
        """Check if the Scylla API is reachable.

        :param scylla: URL of the Scylla API
        :type scylla: str
        :return: Whether Scylla is reachable
        :rtype: boolean
        """

        try:
            url = urllib.parse.urljoin(scylla, SCYLLA_STATS_PATH)
            # Get the proxy list from scylla
            json_resp = requests.get(
                url).json()
            # If the valid_count > 0 then we are good to go!
            if int(json_resp['valid_count']) > 0:
                return True
            else:
                return False

        # Catch and re-raise the exception
        except requests.exceptions.RequestException as e:
            log.exception('Could not reach Scylla.')
            raise e
        except KeyError as e:
            log.exception('Response from Scylla malformed.')
            raise e

    def threading_proxies(self):
        log.info('Starting proxy refresh threading.')
        # Refresh the proxy list
        self.get_proxies()
        # Call this function again after the time elapses
        self.refresh_thread = threading.Timer(
            self.timeout, self.get_proxies)
        # Start the thread
        self.refresh_thread.start()

    def get_proxies(self):
        params = {}
        if self.https:
            params = {'https': 'true'}

        try:
            # Create the url
            url = urllib.parse.urljoin(self.scylla, SCYLLA_API_PATH)
            # Get the proxy list from scylla
            json_resp = requests.get(
                url, params=params).json()
            self.proxies = json_resp['proxies']
        # Catch and re-raise the exception
        except requests.exceptions.RequestException as e:
            log.exception('Could not fetch proxies from Scylla.')
            raise e

    def process_request(self, request, spider):
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
        proxy = random.choice(self.proxies)

        # Format it!
        if self.https:
            proxy_url = 'https://{}:{}'.format(proxy['ip'], proxy['port'])
        else:
            proxy_url = 'http://{}:{}'.format(proxy['ip'], proxy['port'])

        # Set the proxy
        request.meta['proxy'] = proxy_url
        log.info('Using proxy: %s' % proxy_url)

    def process_exception(self, request, exception, spider):
        if 'proxy' not in request.meta:
            return

        # What proxy had the exception
        proxy = request.meta['proxy']

        log.error('Exception using proxy: %s' % exception)
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
        log.info('Closing')
