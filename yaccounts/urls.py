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
    
    # Twitter auth.
    url(r'^/login/twitter/?$', views_twitter.login_request, name='twitter_login'),
    
    # Facebook auth.
    url(r'^/login/facebook/?$', views_facebook.login_request, name='facebook_login')
)