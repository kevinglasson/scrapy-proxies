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
from scrapy_scylla_proxies.exceptions import SSPScyllaNotReachableError, SSPScyllaResponseError, SSPScyllaNoProxiesError

API_PATH = '/api/v1/proxies'
STATS_PATH = '/api/v1/stats'

# String constants
PROXIES = 'proxies'
VALID_COUNT = 'valid_count'

# Parameter constants
LIMIT = 'limit'
MAX_PROXIES_PER_PAGE = 100
HTTPS = 'https'

logger = logging.getLogger('scrapy-scylla-proxies.scylla')


class Scylla(object):
    def __init__(self, uri):
        self.uri = None
        self._check_connection(uri)

    def _check_connection(self, uri):
        """Check if the Scylla API is reachable.

        :param scylla: URL of the Scylla API
        :type scylla: str
        :return: Whether Scylla is reachable
        :rtype: boolean
        """

        logger.debug('Checking connection to Scylla DB.')
        try:
            api = urllib.parse.urljoin(uri, STATS_PATH)
            # Get the proxy list from scylla
            json_resp = requests.get(api).json()

            # If the valid_count > 0 then we are good to go!
            if int(json_resp[VALID_COUNT]) > 0:
                # Set the Scylla uri
                self.uri = uri
            else:
                raise SSPScyllaNoProxiesError(
                    'No proxies in the Scylla DB, might need to wait a minute.')

        # Catch and raise exceptions
        except requests.exceptions.RequestException as e:
            raise SSPScyllaNotReachableError(
                'Could not reach the Scylla API.') from e
        except KeyError as e:
            raise SSPScyllaResponseError(
                'Expected \'%s\' in response, got %s.' % (VALID_COUNT, json_resp)) from e

    def get_proxies(self, https=True):
        """Get proxy address information from Scylla."""

        logger.debug('Fetching proxies.')
        params = {LIMIT: MAX_PROXIES_PER_PAGE}
        if https:
            params[HTTPS] = 'true'

        try:
            # Get the proxy list from scylla
            u = urllib.parse.urljoin(self.uri, API_PATH)
            json_resp = requests.get(
                u, params=params).json()
            return json_resp[PROXIES]
        except requests.exceptions.RequestException as e:
            raise SSPScyllaNotReachableError(
                'Could not reach the Scylla API.') from e
        except ValueError as e:
            raise SSPScyllaResponseError(
                'Response from Scylla when trying to fetch proxies.') from e
