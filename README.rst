===============
django-yaccounts
===============

YACCOUNTS == Yet/Why Another Django Accounts App


Installation
============

1. Download dependencies:
    - Python 2.6+
    - Django 1.5+
    
2. ``pip install django-yaccounts`` or ``easy_install django-yaccounts``


Configuration
=============

settings.py
-----------

1. Add "yaccounts" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = (
        # all other installed apps
        'yaccounts',
    )
      
2. Add logger handler::

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            # all other handlers
            'log_file_yaccounts': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(os.path.join(os.path.dirname( __file__ ), '..'), 'logs/yaccounts.log'),
                'maxBytes': '16777216', # 16megabytes
             },
        },
        'loggers': {
            # all other loggers
            'yaccounts': {
                'handlers': ['log_file_yaccounts'],
                'propagate': True,
                'level': 'DEBUG',
            }
        }
    }
    
3. Configure User model by adding the following line your settings:

``AUTH_USER_MODEL = 'yaccounts.User'``

4. Configure the API URL Namespace where the Yaccounts API will be exposed. Example for when YAPI's URLs live in ``api/v1/``
and the respective Django URL files are::

    # myproject/urls.py
    # ============

    urlpatterns = patterns('',
        # all other url mappings
        url(r'^api', include('myproject.api.urls', namespace='api')),
    )
    
    # myproject/api/urls.py
    # ============

    urlpatterns = patterns('',
        # all other api versions
        url(r'^/v1', include('myproject.api.v1.urls', namespace='myapp')),
    )
    
    # myproject/api/v1/urls.py
    # ============

    urlpatterns = patterns('',
        # all other api url mappings
        url(r'^/account', include('yaccounts.api.urls', namespace='account')),
    )
    
The configuration should be::

    YACCOUNTS = {
        'api_url_namespace': 'api:v1'
    }

Logs
----

Create a 'logs' folder in your project's root folder (if you don't have one already).
Your project folder should look something like this::

    myproject/
        __init__.py
        settings.py
        urls.py
        wsgi.py
    logs/
    manage.py

Database
--------

Run ``python manage.py syncdb`` to create the yaccounts models.

URLs
----

1. Add app URL namespace to top-level ``urls.py``::

    # myproject/urls.py
    # ============

    urlpatterns = patterns('',
       # all other url mappings
       url(r'^account', include('yaccounts.urls', namespace='accounts')),
    )
	
2. Add app to API namespace::

    # myproject/api/urls.py
    # ============
    
    urlpatterns = patterns('',
        # all other api url mappings
        url(r'^/account', include('yaccounts.api.urls', namespace='accounts')),
    )
