#!/usr/bin/env python
import sys
from setuptools import setup

from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='scrapy-scylla-proxies',
    version='0.4.2.1',
    description='scrapy-scylla-proxies: Random proxy middleware for Scrapy that fetches valid proxies from Scylla.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Kevin Glasson',
    author_email='kevinglasson+scrapyscylla@gmail.com',
    url='https://github.com/kevinglasson/scrapy-scylla-proxies.git',
    packages=['scrapy_scylla_proxies'],
    install_requires=['requests', 'attrs'],
    python_requires='>=3',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3'
    ]
)
