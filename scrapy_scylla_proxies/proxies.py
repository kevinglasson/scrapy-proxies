# Code copied and then modified from https://github.com/TeamHG-Memex/scrapy-rotating-proxies/blob/master/rotating_proxies/expire.py

# Copyright (c) scrapy-rotating-proxies developers.
# Copyright (C) 2013 by Kevin Glasson <kevinglasson+scrapyscylla@gmail.com> (Modifications)
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

import logging
import math
import random
import time

import attr

logger = logging.getLogger('scrapy-scylla-proxies.Proxies')


class Proxies(object):
    """
    Expiring proxies container.
    A proxy can be in 3 states:
    * good;
    * dead;
    * unchecked.
    Initially, all proxies are in the 'unchecked' state.
    When a request using a proxy is successful, this proxy moves to the 'good'
    state. When a request using a proxy fails, proxy moves to the 'dead' state.
    For crawling only 'good' and 'unchecked' proxies are used.
    'Dead' proxies move to 'unchecked' after a timeout (they are called
    'reanimated'). This timeout increases exponentially after each
    unsuccessful attempt to use a proxy. Once a proxy has failed 3 times, it will be removed and replaced with a new proxy from Scylla.
    """

    def __init__(self, proxy_list, backoff=None):
        self.proxies = {url: ProxyState() for url in proxy_list}
        self.unchecked = set(self.proxies.keys())
        self.good = set()
        self.dead = set()

        if backoff is None:
            backoff = exp_backoff_full_jitter
        self.backoff = backoff

    def get_random(self):
        """ Return a random available proxy (either good or unchecked) """

        # Join the sets and create a list
        available = list(self.unchecked | self.good)
        if not available:
            return None
        return random.choice(available)

    def get_proxy(self, proxy_address):
        """
        Return complete proxy name associated with a hostport of a given
        ``proxy_address``. If ``proxy_address`` is unkonwn or empty,
        return None.
        """
        if not proxy_address:
            return None
        return

    def mark_dead(self, proxy, _time=None):
        """ Mark a proxy as dead """
        if proxy not in self.proxies:
            logger.warn("Proxy <%s> was not found in proxies list" % proxy)
            return

        if proxy in self.good:
            logger.debug("GOOD proxy became DEAD: <%s>" % proxy)
        else:
            logger.debug("Proxy <%s> is DEAD" % proxy)

        self.unchecked.discard(proxy)
        self.good.discard(proxy)
        self.dead.add(proxy)

        now = _time or time.time()
        state = self.proxies[proxy]
        state.backoff_time = self.backoff(state.failed_attempts)
        state.next_check = now + state.backoff_time
        state.failed_attempts += 1

    def mark_good(self, proxy):
        """ Mark a proxy as good """
        if proxy not in self.proxies:
            logger.warn("Proxy <%s> was not found in proxies list" % proxy)
            return

        if proxy not in self.good:
            logger.debug("Proxy <%s> is GOOD" % proxy)

        self.unchecked.discard(proxy)
        self.dead.discard(proxy)
        self.good.add(proxy)
        self.proxies[proxy].failed_attempts = 0

    def reanimate(self, _time=None):
        """Move dead proxies to unchecked if a backoff timeout passes.
        """
        n_reanimated = 0
        now = _time or time.time()
        for proxy in list(self.dead):
            state = self.proxies[proxy]
            assert state.next_check is not None
            if state.next_check <= now:
                self.dead.remove(proxy)
                self.unchecked.add(proxy)
                n_reanimated += 1
        return n_reanimated

    def reset(self):
        """Mark all dead proxies as unchecked.
        """
        for proxy in list(self.dead):
            self.dead.remove(proxy)
            self.unchecked.add(proxy)

    @property
    def mean_backoff_time(self):
        """Calculate the mean backoff time of the current proxies.
        """
        if not self.dead:
            return 0
        total_backoff = sum(self.proxies[p].backoff_time for p in self.dead)
        return float(total_backoff) / len(self.dead)

    @property
    def reanimated(self):
        return [p for p in self.unchecked if self.proxies[p].failed_attempts]

    def __repr__(self):
        n_reanimated = len(self.reanimated)
        return "Proxies(good: {}, dead: {}, unchecked: {}, reanimated: {}, " \
               "mean backoff time: {}s)".format(
                   len(self.good), len(self.dead),
                   len(self.unchecked) - n_reanimated, n_reanimated,
                   int(self.mean_backoff_time),
               )


@attr.s
class ProxyState(object):
    """Represent the state of a proxy.
    """

    failed_attempts = attr.ib(default=0)
    next_check = attr.ib(default=None)
    backoff_time = attr.ib(default=None)  # for debugging


def exp_backoff(attempt, cap=3600, base=300):
    """ Exponential backoff time.
    """
    # this is a numerically stable version of
    # min(cap, base * 2 ** attempt)
    max_attempts = math.log(cap / base, 2)
    if attempt <= max_attempts:
        return base * 2 ** attempt
    return cap


def exp_backoff_full_jitter(*args, **kwargs):
    """ Exponential backoff time with Full Jitter.
    """
    return random.uniform(0, exp_backoff(*args, **kwargs))
