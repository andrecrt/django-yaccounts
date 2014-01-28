import logging
import oauth2 as oauth
import urlparse
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.core.urlresolvers import reverse
from django.http.response import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.translation import ugettext as _
import twitter
from twitter import TwitterError

# Instantiate logger.
logger = logging.getLogger(__name__)

# Application's OAuth settings.
consumer_key = settings.YACCOUNTS['twitter_oauth']['consumer_key']
consumer_secret = settings.YACCOUNTS['twitter_oauth']['consumer_secret']

# Twitter OAuth URLs.
request_token_url = 'https://api.twitter.com/oauth/request_token'
authorize_url = 'https://api.twitter.com/oauth/authorize'
access_token_url = 'https://api.twitter.com/oauth/access_token'

# Init Twitter API.
consumer = oauth.Consumer(consumer_key, consumer_secret)
client = oauth.Client(consumer)


def login_request(request):
    """
    Starts Twitter authentication.
    """
    
    # Check if Twitter authentication is enabled.
    try:
        settings.YACCOUNTS['signup_available'].index('TWITTER')
    except ValueError:
        messages.add_message(request, messages.ERROR, _('Twitter login not available.'))
        return render_to_response('yaccounts/login.html', context_instance=RequestContext(request))
    
    # If there is an URL to return when login finishes,
    # store it in session in order to make it acessible in
    # the twitter return method (would be better to pass it in the URLs?)
    request.session['login_next'] = request.GET.get('next', reverse('accounts:index'))
    
    # Step 1: Get a request token. This is a temporary token that is used for 
    # having the user authorize an access token and to sign the request to obtain 
    # said access token.
    oauth_callback = settings.HOST_URL + reverse('accounts:twitter_return')
    resp, content = client.request(request_token_url + '?oauth_callback=' + oauth_callback, 'GET')
    if resp['status'] != '200':
        logger.error('Twitter Login Error: unable to request token. ' + content)
        raise Exception("Invalid response %s." % resp['status'])
    request_token = dict(urlparse.parse_qsl(content))
    
    # Add request token to Django session in order to be accessible on oauth callback.
    request.session['request_token'] = request_token
    
    # Step 2: Redirect to the provider.
    return HttpResponseRedirect("%s?oauth_token=%s" % (authorize_url, request_token['oauth_token']))
    
    
def login_return(request):
    """
    OAuth callback.
    """
    
    # If there is no request_token for session,
    # it means we didn't redirect user to Twitter.
    request_token = request.session.get('request_token', None)
    if not request_token:
        messages.add_message(request, messages.ERROR, _('Twitter login error #1'))
        return render_to_response('yaccounts/login.html', context_instance=RequestContext(request))
    
    # If the token from session and token from Twitter does not match,
    # it means something bad happened to tokens.
    elif request_token['oauth_token'] != request.GET.get('oauth_token', None):
        messages.add_message(request, messages.ERROR, _('Twitter login error #2'))
        return render_to_response('yaccounts/login.html', context_instance=RequestContext(request))
    
    
    # Now that we're here, we don't need this in session variables anymore. Cleanup.
    else:
        del request.session['request_token']
    
    # Step 3: Once the consumer has redirected the user back to the oauth_callback
    # URL you can request the access token the user has approved. You use the 
    # request token to sign this request. After this is done you throw away the
    # request token and use the access token returned. You should store this 
    # access token somewhere safe, like a database, for future use.
    token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
    token.set_verifier(request.GET['oauth_verifier'])
    client = oauth.Client(consumer, token)
    
    resp, content = client.request(access_token_url, 'POST')
    access_token = dict(urlparse.parse_qsl(content))
    
    # Verify credentials.
    try:
        api = twitter.Api(consumer_key=consumer_key,
                          consumer_secret=consumer_secret,
                          access_token_key=access_token['oauth_token'],
                          access_token_secret=access_token['oauth_token_secret'])
        userinfo = api.VerifyCredentials()
    except TwitterError:
        messages.add_message(request, messages.ERROR, _('Twitter login error #3'))
        return render_to_response('yaccounts/login.html', context_instance=RequestContext(request))
    
    #
    # Finally, authenticate user with given Twitter credentials.
    #
    user = authenticate(twitter_userinfo=userinfo, twitter_access_token=access_token)
    
    # Account exists with given Twitter profile linked.
    if user:
        
        # If user is active, login account and redirect to next page (if provided, else account profile)
        if user.is_active:
            login(request, user)
            return HttpResponseRedirect(request.session.get('login_next', reverse('accounts:index')))
        
        # User account is inactive.
        else:
            messages.warning(request, _("Your account is disabled."))
            return render_to_response('yaccounts/login.html', context_instance=RequestContext(request))
    
    # Return.
    return HttpResponse(userinfo)