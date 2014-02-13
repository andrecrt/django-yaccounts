from django.conf.urls import patterns, url

import views
import views_facebook
import views_twitter

urlpatterns = patterns('',
                       
    # Account views.
    url(r'^/?$', views.index, name='index'),
    url(r'^/login/?$', views.login_account, name='login'),
    url(r'^/logout/?$', views.logout_account, name='logout'),
    url(r'^/create/?$', views.create_account, name='create'),
    url(r'^/confirm/?$', views.confirm_operation, name='confirm'),
    url(r'^/reset/?$', views.reset_account, name='reset'),
    url(r'^/reset/confirm/?$', views.reset_confirm, name='reset_confirm'),
    
    # Facebook auth.
    url(r'^/login/facebook/?$', views_facebook.login_request, name='facebook_login'),
    url(r'^/login/facebook/return/?$', views_facebook.login_return, name='facebook_return'),
    url(r'^/create/facebook/?$', views_facebook.create_account, name='facebook_create'),
    url(r'^/disconnect/facebook/?$', views_facebook.disconnect_account, name='facebook_disconnect'),
    
    # Twitter auth.
    url(r'^/login/twitter/?$', views_twitter.login_request, name='twitter_login'),
    url(r'^/login/twitter/return/?$', views_twitter.login_return, name='twitter_return'),
    url(r'^/create/twitter/?$', views_twitter.create_account, name='twitter_create'),
    url(r'^/disconnect/twitter/?$', views_twitter.disconnect_account, name='twitter_disconnect')
)