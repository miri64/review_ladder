from django.conf.urls import url

from .views import index, webhook

urlpatterns = [
    url("^$", index),
    url("^webhook/?$", webhook)
]
