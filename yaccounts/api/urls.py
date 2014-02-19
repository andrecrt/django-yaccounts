from django.conf.urls import patterns, url

from handlers import AccountHandler, AccountPhotoHandler, ApiKeysHandler, ApiKeyIdHandler

urlpatterns = patterns('',
    url(r'^/?$', AccountHandler.as_view(), name='index'),
    url(r'^/photo/?$', AccountPhotoHandler.as_view(), name='photo'),
    url(r'^/api_keys/?$', ApiKeysHandler.as_view(), name='api_keys'),
    url(r'^/api_keys/(?P<pk>[0-9]+)/?$', ApiKeyIdHandler.as_view(), name='api_key_id')
)