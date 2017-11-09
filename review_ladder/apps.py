from django.apps import AppConfig

class ReviewLadderConfig(AppConfig):
    name = 'review_ladder'
    verbose_name = "Review Ladder"

    def ready(self):
        from .github import GithubImporter
        import sys

        if not sys.argv[0].endswith("manage.py") or (sys.argv[1] in ["runserver"]):
            GithubImporter().start()
