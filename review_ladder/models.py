from django.db import models, transaction
from django.conf import settings
from django.core import validators

GITHUB_REPO = "%s/%s" % (settings.GITHUB_REPO_USER, settings.GITHUB_REPO_NAME)

# Create your models here.
class User(models.Model):
    id = models.IntegerField(primary_key=True, unique=True)
    avatar_url = models.URLField()
    name = models.CharField(max_length=30, unique=True, db_index=True)

    def __str__(self):
        return self.name

    @property
    def score(self):
        return sum(c.type for c in self.comments.exclude(pr__author=self)) + \
               Comment.MRG * self.merges.count()

    @property
    def stats(self):
        return {
                "approvals": self.comments.filter(type=Comment.ACK).exclude(pr__author=self).count(),
                "change_requests": self.comments.filter(type=Comment.CRQ).exclude(pr__author=self).count(),
                "comments": self.comments.filter(type=Comment.COM).exclude(pr__author=self).count(),
                "merges": self.merges.count(),
            }

    @classmethod
    def from_github_json(cls, json_user):
        return cls.objects.get_or_create(
                id=json_user["id"],
                avatar_url=json_user["avatar_url"],
                name=json_user["login"]
            )

class PullRequest(models.Model):
    class Meta:
        unique_together = (("repo", "number"), )
        indexes = [
                models.Index(fields=("repo", "number")),
            ]

    repo = models.CharField(max_length=100,
                            validators=[validators.RegexValidator("[^/]+/[^/]+")])
    number = models.IntegerField()
    author = models.ForeignKey("User", null=True, blank=True,
                               on_delete=models.SET_NULL)
    assignees = models.ManyToManyField("User", related_name="assignments")

    def __str__(self):
        return "%s#%d" % (self.repo, self.number)

    @classmethod
    def from_github_json(cls, json_pr, json_events=[]):
        with transaction.atomic():
            author, _ = User.from_github_json(json_pr["user"])
            pr, created = cls.objects.update_or_create(
                    repo=GITHUB_REPO,
                    number=json_pr["number"],
                    author=author,
                )
            for json_event in json_events:
                assignee = None
                op = lambda user: None
                if json_event["event"] == "review_requested":
                    assignee, _ = User.from_github_json(json_event["requested_reviewer"])
                    op = pr.assignees.add
                elif json_event["event"] == "assigned":
                    assignee, _ = User.from_github_json(json_event["assignee"])
                    op = pr.assignees.add
                elif json_event["event"] == "review_request_removed":
                    assignee, _ = User.from_github_json(json_event["requested_reviewer"])
                    op = pr.assignees.remove
                elif json_event["event"] == "assigned":
                    assignee, _ = User.from_github_json(json_event["assignee"])
                    op = pr.assignees.remove
                op(assignee)
            pr.save()
        return pr, created

class Comment(models.Model):
    COM = .1    # comment
    CRQ = 4.0   # change request
    ACK = 5.0   # approval
    MRG = 5.0  # merge (not a comment, but to keep the scores together it is here)
    JSON_COMMENT_LOT = {
            "commented": COM,
            "dismissed": COM,
            "changes_requested": CRQ,
            "approved": ACK
        }

    id = models.IntegerField(primary_key=True, unique=True)
    pr = models.ForeignKey("PullRequest", on_delete=models.CASCADE,
                           related_name="comments")
    user = models.ForeignKey("User", on_delete=models.CASCADE,
                             related_name="comments")
    type = models.FloatField(choices=((COM, "comment"),
                                      (CRQ, "change Request"),
                                      (ACK, "approval")),
                             default=COM)

    @classmethod
    def from_github_json(cls, json_comment, pr, type=COM):
        user, _ = User.from_github_json(json_comment["user"])
        return cls.objects.update_or_create(
                id=json_comment["id"],
                pr=pr,
                user=user,
                defaults={"type": type}
            )

    @classmethod
    def from_github_review_json(cls, json_review, pr):
        if json_review["state"].lower() not in cls.JSON_COMMENT_LOT:
            # we don't count "pending" etc.
            return None, False
        return cls.from_github_json(json_review, pr,
                                    cls.JSON_COMMENT_LOT[json_review["state"].lower()])

class Merge(models.Model):
    sha = models.CharField(max_length=40,
                           validators=[validators.RegexValidator("[a-f0-9A-F]+")],
                           primary_key=True, unique=True)
    pr = models.OneToOneField("PullRequest")
    author = models.ForeignKey("User", related_name="merges")

    def __str__(self):
        return self.sha[:7]

    @classmethod
    def from_github_json(cls, json_commit, pr):
        author, _ = User.from_github_json(json_commit["author"])
        return cls.objects.get_or_create(
                sha=json_commit["sha"],
                author=author,
                pr=pr
            )
