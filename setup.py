#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (C) 2017 Freie Universität Berlin
#
# Distributed under terms of the MIT license.

import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='review-ladder',
    version='0.1.2',
    packages=find_packages(),
    include_package_data=True,
    license='MIT License',
    description='A django app that rates the performance of the maintainers of a GitHub project and displays them as a Top 20 ladder.',
    long_description=README,
    url='https://www.todo.com/',
    author='Martine Lenders',
    author_email='m.lenders@fu-berlin.de',
    install_requires=["django>=1.11", "python-dateutil", "ipaddress", "requests", "schedule"],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.11',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
