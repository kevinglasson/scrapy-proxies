#!/usr/bin/env python
import sys
from distutils.core import setup

setup(
    name='scrapy-scylla-proxies',
    version='0.1.4.0',
    description='Scrapy-Scylla Proxies: random proxy middleware for Scrapy',
    author='Kevin Glasson',
    author_email='kevinglasson+scrapyscylla@gmail.com',
    url='https://github.com/kevinglasson/scrapy-scylla-proxies.git',
    packages=['scrapy_scylla_proxies'],
    install_requires=['requests'],
    python_requires='>=3',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3'
    ]
)
