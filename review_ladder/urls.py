from django.conf.urls import url

from .views import index, assignments, webhook

urlpatterns = [
    url("^$", index, name="score"),
    url("^assignments/$", assignments, name="assignments"),
    url("^webhook/?$", webhook)
]
