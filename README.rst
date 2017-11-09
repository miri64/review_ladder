=============
Review Ladder
=============

Review Ladder is an application that rates performances of the reviewers of a
GitHub project. Scorings are applied for number of approvals, change requests,
comments and merges (see self-documentation when application is running for the
specifics of the scoring system).

Quick start
-----------

1. Install this app::

    pip install .

2. If you did not already, start a django project::

    cd ..
    django-admin startproject <projectname>
    cd <projectname>

3. Add "review_ladder" to your INSTALLED_APPS setting in your project's
   setting.py like this::

    INSTALLED_APPS = [
        ...
        'review_ladder',
    ]

4. Add the following options to your project's settings.py to access GitHub::

    GITHUB_API = "https://api.github.com"   # The link to the GitHub API
    GITHUB_USER = "<user name>"             # A GitHub user name
    GITHUB_PW = "<password>"                # Password
    GITHUB_REPO_USER = "<user or org name>" # User or org name of the project's repo
    GITHUB_REPO_NAME = "<repo name>"        # Name of the project's repo you want to rate

   As a password we recommend a `Personal Access Token <https://github.com/settings/tokens>`_.

5. Include the review_ladder URLconf in your project's urls.py like this::

    url('^review_ladder/', include('review_ladder.urls'))

4. Run ``python3 manage.py makemigrations && python3 manage.py migrate`` to
   create the review_ladder models.

5. If you configured your project to use SQLite you might want to
   `increase the timeout to prevent "database is locked" errors
   <https://docs.djangoproject.com/en/dev/ref/databases/#database-is-locked-errors>`_.

6. Start the development server using ``python3 manage.py runserver`` and visit
   http://127.0.0.1:8000/review_ladder to watch the Top 20 being build from
   GitHub data

7. To keep the ladder live up-to-date configure a
   `webhook <https://help.github.com/articles/about-webhooks/>`_
   to https://example.com/review_ladder/webhook (replace `example.com` with the
   servers domain) for the following events:

   - Pull Request
   - Pull Request review
   - Pull Request review comment

   For more security you can a secret to the webhook and configure it in your
   project's setting.py using the `GITHUB_WEBHOOK_KEY` variable.
