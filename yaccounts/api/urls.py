from django.conf.urls import patterns, url

from handlers import AccountHandler, AccountPhotoHandler, ApiKeysHandler, ApiKeyIdHandler
from yapi.resource import Resource

urlpatterns = patterns('',
    url(r'^/?$', Resource(AccountHandler), name='index'),
    url(r'^/photo/?$', Resource(AccountPhotoHandler), name='photo'),
    url(r'^/api_keys/?$', Resource(ApiKeysHandler), name='api_keys'),
    url(r'^/api_keys/(?P<pk>[0-9]+)/?$', Resource(ApiKeyIdHandler), name='api_key_id')
)