=====
Yaccounts (Yet/Why Another Django Accounts App)
=====

Yaccounts is an accounts app for Django.

Quick start
-----------

1. Add "yaccounts" to your INSTALLED_APPS setting like this:

      INSTALLED_APPS = (
          ...
          'yaccounts',
      )
      
2. Create a 'logs' folder on your project's folder (if you don't have one already).
      
3. Add logger handler:

      LOGGING = {
          'version': 1,
          'disable_existing_loggers': False,
          'handlers': {
            ...
            'log_file_yaccounts': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(os.path.join(os.path.dirname( __file__ ), '..'), 'logs/yaccounts.log'),
                'maxBytes': '16777216', # 16megabytes
            },
        },
        'loggers': {
            ...
            'yaccounts': {
                'handlers': ['log_file_yaccounts'],
                'propagate': True,
                'level': 'DEBUG',
            }
        }
    }
    
4. Configure User model by adding the following line your settings:

	AUTH_USER_MODEL = 'yaccounts.User'

5. Run `python manage.py syncdb` to create the yaccounts models.

6. Add app to URLs:

	url(r'^account', include('yaccounts.urls', namespace='accounts'))
	
7. Add app to API URL:

	url(r'^/account', include('yaccounts.api.urls', namespace='accounts'))