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
import dateutil.parser
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

REMAINING = None
UNTIL = None

def get(url, *args, **kwargs):
    global REMAINING, UNTIL
    if (REMAINING != None) and (UNTIL != None):
        # rate limit
        seconds = (UNTIL - datetime.datetime.now()).total_seconds() / REMAINING
        LOGGER.debug("Rate limitation: sleeping for %f" % seconds)
        if seconds > 0:
            time.sleep(seconds)
    if GITHUB_AUTH:
        kwargs["auth"] = GITHUB_AUTH
    res = requests.get(url, *args, **kwargs)
    LOGGER.debug("Got %s (code: %d%s)" % \
            (res.url, res.status_code, ", authenticated" if kwargs.get("auth", None) else ""))
    REMAINING = int(res.headers.get("x-ratelimit-remaining", 5000))
    UNTIL = datetime.datetime.fromtimestamp(
            int(res.headers.get("x-ratelimit-reset", time.time() + (60 * 60)))
        )
    if (REMAINING == 0) or (res.status_code == 403):
        seconds = (UNTIL - datetime.datetime.now()).total_seconds()
        LOGGER.debug("Rate limitation: sleeping for %f" % seconds)
        if seconds > 0:
            time.sleep(seconds)
        get(url, *args, **kwargs)
    return res

def github_json_pagination(url, params={}, page=1):
    last = 1
    while page <= last:
        params["page"] = page
        res = get(url, params=params)
        if "Link" in res.headers:
            match = re.search(r'page=(\d+)[^>]*>; rel="last"', res.headers['Link'])
            if match:
                last = int(match.group(1))
        for item in res.json():
            yield item
        page += 1

def github_json_search_pagination(url, params={}, page=1):
    last = 1
    while page <= last:
        params["page"] = page
        res = get(url, params=params)
        if "Link" in res.headers:
            match = re.search(r'page=(\d+)[^>]*>; rel="last"', res.headers['Link'])
            if match:
                last = int(match.group(1))
        for item in res.json().get("items", []):
            yield item
        page += 1

def json_hooks():
    return get('%s/meta' % settings.GITHUB_API).json().get("hooks", [])

def json_prs(page=1):
    if hasattr(settings, "GITHUB_SINCE"):
        since_str = dateutil.parser.parse(settings.GITHUB_SINCE).isoformat()
        return github_json_search_pagination(
                '%s/search/issues' % (settings.GITHUB_API),
                {
                    "q": "repo:%s type:pr updated:>=%s" % (GITHUB_REPO, settings.GITHUB_SINCE),
                    "sort": "updated",
                },
                page=page
            )
    else:
        return github_json_pagination(
                '%s/repos/%s/pulls' % (settings.GITHUB_API, GITHUB_REPO),
                {"state": "all"},
                page=page
            )

def json_issue_events(issue, page=1):
    return github_json_pagination(
            '%s/repos/%s/issues/%d/events' % (settings.GITHUB_API, GITHUB_REPO, issue),
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
            pr, _ = PullRequest.from_github_json(json_pr, json_issue_events(
                    json_pr["number"]
                ))
            with transaction.atomic():
                for json_comment in json_comments(pr.number):
                    Comment.from_github_json(json_comment, pr)
                for json_review in json_reviews(pr.number):
                    Comment.from_github_review_json(json_review, pr)
            if ("merged_at" not in json_pr) and json_pr["state"] == "closed":
                # PR data came through search => we need to get the actual object
                res = get('%s/repos/%s/pulls/%d' % (settings.GITHUB_API, GITHUB_REPO, pr.number))
                json_pr = res.json()
            if json_pr.get("merged_at", None):
                c = json_commit(json_pr["merge_commit_sha"])
                if "author" not in c:
                    # HTTP error returned an empty object
                    continue
                Merge.from_github_json(c, pr)
        except OperationalError as e:
            continue    # skip for now and try in next round

import_schedule = schedule.every().day.do(import_models)

class GithubImporter(threading.Thread):
    def run(self):
        while True:
            import_schedule.run()
            schedule.run_pending()
            time.sleep(3600)
