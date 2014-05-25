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

4. Configure authentication backends to enable Yaccount's authentication backends (e.g. Authentication Key, Twitter, etc) for account email confirmation::

    AUTHENTICATION_BACKENDS = (
        'django.contrib.auth.backends.ModelBackend',
        'yaccounts.backends.ActivationKeyAuthenticationBackend',
        'yaccounts.backends.TwitterBackend',
        'yaccounts.backends.FacebookBackend'
    )

5. Configure YACCOUNT's settings::

    YACCOUNTS = {
    	# API URL Namespace (e.g. YAPI URL is in /api/v1, and the respective Django URL namespaces are 'api' and 'v1')
        'api_url_namespace': 'api:v1',
        
        # Enabled signup types (possible: 'EMAIL', 'FACEBOOK', 'TWITTER', 'API')
        'signup_available': ['EMAIL'], # Only email signup enabled
        
        # Application emails 'sender'.
        'email_from': { 'name': 'Administrator', 'email': 'admin@example.com' },
        
        # Twitter Application's OAuth Settings.
        'twitter_oauth': {
            'consumer_key': '{{ YOUR_APP_CONSUMER_KEY }}',
            'consumer_secret': '{{ YOUR_APP_CONSUMER_SECRET }}'
        },
        
        # Facebook Application's OAuth Settings.
        'facebook_oauth': {
	         'app_id': '{{ APP_ID }}',
	         'app_secret': '{{ APP_SECRET }}'
	    }
    }

6. Don't forget to set the 'MEDIA_URL' variable, which defines the root folder to where files will be uploaded (e.g. profile pictures) and the
variable necessary for the full URL's of the pictures to be built::

    MEDIA_ROOT = os.path.join(BASE_DIR, 'static/uploads/')
    MEDIA_URL = HOST_URL + '/static/uploads/'
    
7. Configure template processors so tha every RequestContext will contain a variable request, which is the current HttpRequest. This will be used for stuff
such as knowing the current path. 

    from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS as TCP
    TEMPLATE_CONTEXT_PROCESSORS = TCP + (
        'django.core.context_processors.request',
    )

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
       url(r'^account', include('yaccounts.urls', namespace='yaccounts')),
    )
	
2. Add app to API namespace::

    # myproject/api/urls.py
    # ============
    
    urlpatterns = patterns('',
        # all other api url mappings
        url(r'^/account', include('yaccounts.api.urls', namespace='yaccounts')),
    )
