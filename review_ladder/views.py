from django.conf import settings
from django.db.models import Q, Count
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden
from django.http import HttpResponseBadRequest, HttpResponseServerError
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST
from django.shortcuts import render
from django.utils.encoding import force_bytes, force_str
from django.views.decorators.csrf import csrf_exempt

import dateutil.parser
import hmac
from hashlib import sha1
from ipaddress import ip_address, ip_network
try:
    import simplejson as json
except ImportError:
    import json

# Create your views here.
from .models import Comment, Merge, PullRequest, User
from .github import *

@cache_page(2 * 60)
def index(request):
    maintainers = sorted(User.objects
                            .annotate(comments_num=Count("comments"))
                            .annotate(merges_num=Count("merges"))
                            .filter(Q(comments_num__gt=0) | Q(merges_num__gt=0)),
                         key=lambda u: u.score,
                         reverse=True)
    context = {
            "repository": GITHUB_REPO,
            # score can still be 0 if comments were made in own PR
            "maintainers": [m for m in maintainers if m.score > 0][:20],
            "scores": {
                    "comment": Comment.COM,
                    "change_request": Comment.CRQ,
                    "approval": Comment.ACK,
                    "merge": Comment.MRG,
                }
        }
    if hasattr(settings, "GITHUB_SINCE"):
        context["since"] = dateutil.parser.parse(settings.GITHUB_SINCE)
    return render(request, "review_ladder/index.html", context)

@cache_page(2 * 60)
def assignments(request):
    maintainers = (User.objects
                            .annotate(assignments_num=Count("assignments"))
                            .filter(assignments_num__gt=0)
                            .order_by("-assignments_num"))
    context = {
            "repository": GITHUB_REPO,
            # score can still be 0 if comments were made in own PR
            "maintainers": maintainers.all()[:20],
        }
    if hasattr(settings, "GITHUB_SINCE"):
        context["since"] = dateutil.parser.parse(settings.GITHUB_SINCE)
    return render(request, "review_ladder/assignments.html", context)

class HttpErrorResponse(Exception):
    def __init__(self, response):
        self.response = response

def verify_request_source(request):
    # Verify if request came from GitHub
    forwarded_for = u'{}'.format(request.META.get('HTTP_X_FORWARDED_FOR'))
    client_ip_address = ip_address(forwarded_for.split(",")[0])
    whitelist = json_hooks()

    for valid_ip in whitelist:
        if client_ip_address in ip_network(valid_ip):
            return
    else:
        raise HttpErrorResponse(HttpResponseForbidden('Permission denied.'))

def verify_request_signature(request):
    # Verify the request signature
    header_signature = request.META.get('HTTP_X_HUB_SIGNATURE')
    if header_signature is None:
        raise HttpErrorResponse(HttpResponseForbidden('Permission denied.'))

    sha_name, signature = header_signature.split('=')
    if sha_name != 'sha1':
        raise HttpErrorResponse(HttpResponseServerError('Operation not supported.',
            status=501))

    mac = hmac.new(force_bytes(settings.GITHUB_WEBHOOK_KEY),
                   msg=force_bytes(request.body), digestmod=sha1)
    if not hmac.compare_digest(force_bytes(mac.hexdigest()),
                               force_bytes(signature)):
        raise HttpErrorResponse(HttpResponseForbidden('Permission denied.'))

def handle_pull_request_event(data):
    if (data["repository"]["full_name"] != GITHUB_REPO):
        return HttpResponseBadRequest("Unexpected data")
    json_pr = data["pull_request"]
    if (data["action"] == "opened") or \
        ((data["action"] == "closed") and json_pr["merged"]):
        pr, _ = PullRequest.from_github_json(json_pr)
        if (data["action"] == "closed") and json_pr["merged"]:
            c = json_commit(json_pr["merge_commit_sha"])
            if (c.get("author")):
                Merge.from_github_json(c, pr)
    if (data["action"] in ["assigned", "unassigned", "review_requested",
                           "review_request_removed"]):
        if data["action"] in ["assigned", "unnassigned"]:
            json_assignee = data["assignee"]
        else:
            json_assignee = data["requested_reviewer"]
        with transaction.atomic():
            pr, _ = PullRequest.from_github_json(json_pr)
            assignee, _ = User.from_github_json(json_assignee)
            if data["action"] in ["assigned", "review_requested"]:
                pr.assignees.add(assignee)
            else:
                pr.assignees.remove(assignee)
            pr.save()
    return HttpResponse("Done")

def handle_pull_request_review_event(data):
    if (data["repository"]["full_name"] != GITHUB_REPO):
        return HttpResponseBadRequest("Unexpected data")
    json_review = data["review"]
    if data["action"] == "submitted":
        pr, _ = PullRequest.from_github_json(data["pull_request"])
        Comment.from_github_review_json(json_review, pr)
    elif data["action"] == "dismissed":
        # degrade review to a comment
        comment = Comment.objects.filter(id=json_review["id"]).update(type=Comment.COM)
    return HttpResponse("Done")

def handle_pull_request_comment_event(data):
    if (data["repository"]["full_name"] != GITHUB_REPO):
        return HttpResponseBadRequest("Unexpected data")
    json_comment = data["comment"]
    if data["action"] == "created":
        pr, _ = PullRequest.from_github_json(data["pull_request"])
        Comment.from_github_json(json_comment, pr)
    elif data["action"] == "deleted":
        Comment.objects.filter(id=json_comment["id"]).delete()
    return HttpResponse("Done")

@csrf_exempt
@require_POST
def webhook(request):
    try:
        verify_request_source(request)
        if hasattr(settings, "GITHUB_WEBHOOK_KEY"):
            verify_request_signature(request)
    except HttpErrorResponse as e:
        return e.response
    if request.content_type != "application/json":
        return HttpResponseBadRequest("Expecting JSON data")
    event = request.META.get('HTTP_X_GITHUB_EVENT', None)

    if event == "ping":
        return HttpResponse("pong")
    elif event == "pull_request":
        return handle_pull_request_event(json.loads(force_str(request.body)))
    elif event == "pull_request_review":
        return handle_pull_request_review_event(json.loads(force_str(request.body)))
    elif event == "pull_request_review_comment":
        return handle_pull_request_comment_event(json.loads(force_str(request.body)))

    return HttpResponse(status=204)
