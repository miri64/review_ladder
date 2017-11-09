#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (C) 2017 Freie Universität Berlin
#
# Distributed under terms of the MIT license.

import os
from setuptools import find_packages, setup

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='review-ladder',
    version='0.0.0.dev0',
    packages=find_packages(),
    include_package_data=True,
    license='MIT License',
    description='A tier for scoring reviews of the maintainers of a repository.',
    url='https://www.todo.com/',
    author='Martine Lenders',
    author_email='m.lenders@fu-berlin.de',
    install_requires=["requests"],
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
