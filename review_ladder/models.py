from django.db import models
from django.core import validators

# Create your models here.
class User(models.Model):
    id = models.IntegerField(primary_key=True, unique=True)
    avatar_url = models.URLField()
    name = models.CharField(max_length=30, unique=True)

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

class PullRequest(models.Model):
    class Meta:
        unique_together = (("repo", "number"), )

    id = models.IntegerField(primary_key=True, unique=True)
    repo = models.CharField(max_length=100,
                            validators=[validators.RegexValidator("[^/]+/[^/]+")])
    number = models.IntegerField()
    author = models.ForeignKey("User", null=True, blank=True,
                               on_delete=models.SET_NULL)

    def __str__(self):
        return "%s#%d" % (self.repo, self.number)


class Comment(models.Model):
    COM = 1.0   # comment
    CRQ = 4.0   # change request
    ACK = 5.0   # approval
    MRG = 3.0   # merge (not a comment, but to keep the scores together it is here)

    id = models.IntegerField(primary_key=True, unique=True)
    pr = models.ForeignKey("PullRequest", on_delete=models.CASCADE,
                           related_name="comments")
    user = models.ForeignKey("User", on_delete=models.CASCADE,
                             related_name="comments")
    type = models.FloatField(choices=((COM, "comment"),
                                      (CRQ, "change Request"),
                                      (ACK, "approval")),
                             default=COM)

class Merge(models.Model):
    sha = models.CharField(max_length=40,
                           validators=[validators.RegexValidator("[a-f0-9A-F]+")],
                           primary_key=True, unique=True)
    pr = models.OneToOneField("PullRequest")
    author = models.ForeignKey("User", related_name="merges")

    def __str__(self):
        return self.sha[:7]
