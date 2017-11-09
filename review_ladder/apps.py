from django.apps import AppConfig

class ReviewLadderConfig(AppConfig):
    name = 'review_ladder'

    def ready(self):
        from .github import GithubImporter
        import sys

        if sys.argv[1] in ["runserver"]:
            GithubImporter().start()
