#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2017 Erigones, s. r. o.
# All Rights Reserved
#
# This software is licensed as described in the README.rst and LICENSE
# files, which you should have received as part of this distribution.
import os

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# noinspection PyPep8Naming
from zabbix_api import __version__ as VERSION

read = lambda fname: open(os.path.join(os.path.dirname(__file__), fname)).read()

CLASSIFIERS = [
    'Environment :: Console',
    'Environment :: Plugins',
    'Intended Audience :: System Administrators',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 3',
    'Development Status :: 5 - Production/Stable',
    'Topic :: Software Development :: Libraries',
    'Topic :: System :: Monitoring',
    'Topic :: Utilities'
]

setup(
    name='zabbix-api-erigones',
    version=VERSION,
    description='Zabbix API Python Library',
    long_description=read('README.rst'),
    url='https://github.com/erigones/zabbix-api/',
    author='Erigones',
    author_email='erigones@erigones.com',
    license='LGPL',
    py_modules=['zabbix_api'],
    platforms='any',
    classifiers=CLASSIFIERS,
    include_package_data=True
)
