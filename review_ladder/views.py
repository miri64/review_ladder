from django.conf import settings
from django.db.models import Q, Count
from django.shortcuts import render

# Create your views here.
from .models import User, Comment
from .github import *

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
    return render(request, "review_ladder/index.html", context)
