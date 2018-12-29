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

import requests

log = logging.getLogger('scrapy-scylla.proxies')

SCYLLA_API_PATH = '/api/v1/proxies'


class RandomProxy(object):
    def __init__(self, settings):
        # Location of the scylla JSON api endpoint
        self.scylla = settings.get('SCYLLA_URI')
        # How often to get a new list of proxies from scylla
        self.timeout = settings.get('PROXY_TIMEOUT')
        # The current list of proxies to choose from
        self.proxies = None
        # HTTPS only
        self.https = settings.get('PROXY_HTTPS')
        # Keep a handle on the proxy refresh thread
        self.refresh_thread = None
        # Refresh the proxies list (or populate if it's the first time)
        self.threading_proxies()
        # Exception if the list is empty for some reason
        if self.proxies is None:
            raise ValueError('Proxies list is empty')

    def threading_proxies(self):
        log.info('Starting proxy refresh threading')
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
            log.exception('Could not fetch proxies from scylla.')
            raise e

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

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
        log.info('Closing scrapy-scylla-proxies middleware')
