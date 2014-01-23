from django.conf.urls import patterns, url

import views

urlpatterns = patterns('',
                       
    url(r'^/?$', views.index, name='index'),
    url(r'^/login/?$', views.login_account, name='login'),
    url(r'^/logout/?$', views.logout_account, name='logout'),
    url(r'^/create/?$', views.create_account, name='create'),
    url(r'^/confirm/?$', views.confirm_operation, name='confirm'),
    url(r'^/reset/?$', views.reset_account, name='reset'),
    url(r'^/reset/confirm/?$', views.reset_confirm, name='reset_confirm')
)