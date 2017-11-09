#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (C) 2017 Martine Lenders <m.lenders@fu-berlin.de>
#
# Distributed under terms of the MIT license.

from django.conf import settings
from django.db import transaction
from django.db.utils import OperationalError

import datetime
import logging
import requests
import re
import schedule
import threading
import time

from .models import Comment, Merge, PullRequest, User

if settings.GITHUB_USER and settings.GITHUB_PW:
    GITHUB_AUTH = requests.auth.HTTPBasicAuth(settings.GITHUB_USER,
                                              settings.GITHUB_PW)
else:
    GITHUB_AUTH = None

LOGGER = logging.getLogger(__name__)
GITHUB_REPO = "%s/%s" % (settings.GITHUB_REPO_USER, settings.GITHUB_REPO_NAME)
RATE_LIMIT_WAIT = 60

GETS = 1
LAST_WAIT = datetime.datetime.now()

def get(url, *args, **kwargs):
    global GETS, LAST_WAIT
    if (GETS % 5000) == 0:
        if ((datetime.datetime.now() - LAST_WAIT) < datetime.timedelta(hours=1)):
            # wait because of rate limitation
            time.sleep((datetime.datetime.now() - LAST_WAIT).total_seconds() + 5)
            LAST_WAIT = datetime.datetime.now()
    kwargs["auth"] = GITHUB_AUTH
    LOGGER.debug("Get %s", url)
    res = requests.get(url, *args, **kwargs)
    GETS += 1
    if res.status_code == 403:
        # wait because of rate limitation
        LOGGER.error("Reached rate limitation. Sleeping for %u sec" % \
                     ((datetime.datetime.now() - LAST_WAIT).total_seconds() + 5))
        time.sleep((datetime.datetime.now() - LAST_WAIT).total_seconds() + 5)
        LAST_WAIT = datetime.datetime.now()

    return res

def github_json_pagination(url, params={}, page=1):
    last = 1
    while page <= last:
        params["page"] = page
        res = get(url, params=params)
        if res.status_code != 200:
            break
        if "Link" in res.headers:
            match = re.search(r'page=(\d+)[^>]*>; rel="last"', res.headers['Link'])
            if match:
                last = int(match.group(1))
        for pr in res.json():
            yield pr
        page += 1

def json_hooks():
    return get('%s/meta' % settings.GITHUB_API).json().get("hooks", [])

def json_prs(page=1):
    return github_json_pagination(
            '%s/repos/%s/pulls' % (settings.GITHUB_API, GITHUB_REPO),
            {"state": "all"},
            page=page
        )

def json_comments(pr, page=1):
    return github_json_pagination(
            '%s/repos/%s/pulls/%d/comments' % (settings.GITHUB_API, GITHUB_REPO, pr),
            page=page
        )

def json_reviews(pr, page=1):
    return github_json_pagination(
            '%s/repos/%s/pulls/%d/reviews' % (settings.GITHUB_API, GITHUB_REPO, pr),
            page=page
        )

def json_commit(sha):
    res = get('%s/repos/%s/commits/%s' % (settings.GITHUB_API, GITHUB_REPO, sha))
    return res.json()

def import_models(pr_page=1):
    for json_pr in json_prs(pr_page):
        try:
            pr, _ = PullRequest.from_github_json(json_pr)
            with transaction.atomic():
                for json_comment in json_comments(pr.number):
                    Comment.from_github_json(json_comment, pr)
                for json_review in json_reviews(pr.number):
                    Comment.from_github_review_json(json_review, pr)
            if json_pr["merged_at"]:
                c = json_commit(json_pr["merge_commit_sha"])
                if "author" not in c:
                    # HTTP error returned an empty object
                    continue
                Merge.from_github_json(c, pr)
        except OperationalError as e:
            continue    # skip for now and try in next round

schedule.every().day.do(import_models)

class GithubImporter(threading.Thread):
    def run(self):
        while True:
            import_models()
            schedule.run_pending()
            time.sleep(3600)
