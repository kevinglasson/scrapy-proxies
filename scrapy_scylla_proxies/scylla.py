# For interacting with the Scylla API
import base64
import logging
import random
import re
import threading
import urllib.parse

import requests
from scrapy import signals
from scrapy.exceptions import CloseSpider, NotConfigured
from scrapy_scylla_proxies.exceptions import SSPScyllaNotReachable, SSPScyllaResponseError

SCYLLA_API_PATH = '/api/v1/proxies'
SCYLLA_STATS_PATH = '/api/v1/stats'

logger = logging.getLogger('scrapy-scylla-proxies.Scylla')


class ScyllaAPI(object):
    def __init__(self, url):
        self.scylla = None

        # Check scylla is alive and set the URL
        if ScyllaAPI.scylla_alive_and_populated(url):
            self.scylla = url
        else:
            raise NotConfigured(
                'Scylla not configured correctly or reachable.')

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

        # Catch and raise exceptions
        except requests.exceptions.RequestException:
            raise SSPScyllaNotReachable('Could not reach the API')
        except KeyError:
            raise SSPScyllaResponseError(
                'Expected \'valid_count\' in response, got %s' % json_resp)
