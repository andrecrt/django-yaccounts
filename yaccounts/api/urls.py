from django.conf.urls import patterns, url

from handlers import AccountHandler,  ApiKeysHandler, ApiKeyIdHandler, AccountPhotoHandler, AuthenticationHandler, AccountRegisterHandler

urlpatterns = patterns('',
    url(r'^/?$', AccountHandler.as_view(), name='index'),
    url(r'^/api_keys/?$', ApiKeysHandler.as_view(), name='api_keys'),
    url(r'^/api_keys/(?P<pk>[0-9]+)/?$', ApiKeyIdHandler.as_view(), name='api_key_id'),
    url(r'^/authenticate/?$', AuthenticationHandler.as_view(), name='authenticate'),
    url(r'^/photo/?$', AccountPhotoHandler.as_view(), name='photo'),
    url(r'^/register/?$', AccountRegisterHandler.as_view(), name='register')
)