from django.conf.urls import patterns, url

from handlers import AccountHandler, AccountPhotoHandler
from yapi.resource import Resource

urlpatterns = patterns('',
    url(r'^/?$', Resource(AccountHandler), name='index'),
    url(r'^/photo/?$', Resource(AccountPhotoHandler), name='photo')
)