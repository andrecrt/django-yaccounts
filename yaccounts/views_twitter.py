import datetime
import json
import logging
import oauth2 as oauth
import urlparse
import twitter
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.core.validators import validate_email
from django.db.utils import IntegrityError
from django.http.response import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.translation import ugettext as _
from yapi.utils import generate_key

from models import AuthenticationLog, TwitterProfile

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


class UserInfo:
    """
    Twitter userinfo wrapper.
    (if necessary to have an object similar to what is returned by the twitter lib)
    """
    def __init__(self, twitter_user_id, screen_name):
        self.id = twitter_user_id
        self.screen_name = screen_name


def login_request(request):
    """
    Starts Twitter authentication.
    """
    
    # Check if Twitter authentication is enabled.
    try:
        settings.YACCOUNTS['signup_available'].index('TWITTER')
    except ValueError:
        messages.add_message(request, messages.ERROR, _('Twitter login not available.'))
        return HttpResponseRedirect(reverse('yaccounts:index'))
    
    # If there is an URL to return when login finishes,
    # store it in session in order to make it acessible in
    # the twitter return method (would be better to pass it in the URLs?)
    request.session['login_next'] = request.GET.get('next', reverse('yaccounts:index'))
    
    # Step 1: Get a request token. This is a temporary token that is used for 
    # having the user authorize an access token and to sign the request to obtain 
    # said access token.
    oauth_callback = settings.HOST_URL + reverse('yaccounts:twitter_return')
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
        return HttpResponseRedirect(reverse('yaccounts:index'))
    
    # If the token from session and token from Twitter does not match,
    # it means something bad happened to tokens.
    elif request_token['oauth_token'] != request.GET.get('oauth_token', None):
        messages.add_message(request, messages.ERROR, _('Twitter login error #2'))
        return HttpResponseRedirect(reverse('yaccounts:index'))
    
    
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
    except twitter.TwitterError:
        messages.add_message(request, messages.ERROR, _('Twitter login error #3'))
        return HttpResponseRedirect(reverse('yaccounts:index'))
    
    #
    # Finally, authenticate user with given Twitter credentials.
    #
    user = authenticate(twitter_userinfo=userinfo, twitter_access_token=access_token)
    
    ##
    # a) Twitter profile is linked with existing user account.
    if user:
        
        # Additional information on the request that should be logged.
        metadata = { 'user_agent': request.META['HTTP_USER_AGENT'] }
        
        # If user is active, login account and redirect to next page (if provided, else account profile)
        if user.is_active:
            
            # Create user login session.
            login(request, user)
            
            # Log authentication.
            AuthenticationLog.new(email=user.email,
                                  valid_credentials=True,
                                  credentials_type='twitter',
                                  account_status='active',
                                  success=True,
                                  ip_address=request.META['REMOTE_ADDR'],
                                  metadata=json.dumps(metadata))
            
            # Redirect to either page referenced as next or accounts index.
            return HttpResponseRedirect(request.session.get('login_next', reverse('yaccounts:index')))
        
        # User account is inactive.
        else:
            
            # Log authentication.
            AuthenticationLog.new(email=user.email,
                                  valid_credentials=True,
                                  credentials_type='twitter',
                                  account_status='disabled',
                                  success=False,
                                  ip_address=request.META['REMOTE_ADDR'],
                                  metadata=json.dumps(metadata))
            
            # Message.
            messages.warning(request, _("Your account is disabled."))
            
            # Return.
            return HttpResponseRedirect(reverse('yaccounts:login'))
        
    ##
    # b) Unknown Twitter profile.
    else:
        
        # i) If there is an account logged in, (attempt to) link the Twitter profile with it.
        if request.user.is_authenticated():
            try:
                TwitterProfile.new(user=request.user, userinfo=userinfo, access_token=access_token)
                messages.success(request, _("Twitter account connected successfully."))
            except IntegrityError:
                messages.error(request, _("You already have a Twitter profile linked to your account."))
            return HttpResponseRedirect(reverse('yaccounts:index'))
        
        # ii) Create new account.
        else:
            # Place Twitter info in a session variable in order for it to be accessed in the registration page.
            request.session['twitter_create'] = {
                    'twitter_user_id': userinfo.id,
                    'screen_name': userinfo.screen_name,
                    'profile_image_url': userinfo.profile_image_url,
                    'name': userinfo.name,
                    'access_token': access_token,
                    'expires': (datetime.datetime.now() + datetime.timedelta(seconds=5*60)).strftime('%s') # Convert to epoch to be JSON serializable.
            }
            return HttpResponseRedirect(reverse('yaccounts:twitter_create'))


def create_account(request):
    """
    Create new account with Twitter credentials.
    """
    
    #
    # Lets validate if we should be here.
    #
    
    # If user is authenticated, then this place shouldn't be reached.
    # Twitter profile, if valid, should be linked with the logged in account and not create a new account.
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('yaccounts:index'))
    
    # In order to create account with Twitter profile, its details should have been stored in session.
    twitter_create = request.session.get('twitter_create', None)
    if not twitter_create:
        messages.error(request, _('Twitter login error #4'))
        return HttpResponseRedirect(reverse('yaccounts:login'))
    
    # If time window for registration of new account with this Twitter profile has expired,
    # delete it from session and restart Twitter login process.
    if datetime.datetime.now() > datetime.datetime.fromtimestamp(float(twitter_create['expires'])):
        del request.session['twitter_create']
        return HttpResponseRedirect(reverse('yaccounts:twitter_login'))
    
    #
    # Proceed with account creation.
    #
    email = ''
    
    # A form was received.
    if request.method == 'POST':
        
        proceed = True
        
        # Fetch mandatory params.
        try:
            email = request.POST['email']
        except KeyError:
            proceed = False
            messages.error(request, _("Please provide an e-mail address."))
            
        # Validate email address.
        try:
            validate_email(email)
        except ValidationError:
            proceed = False
            messages.error(request, _("Please provide a valid email address."))
            
        # Check if Twitter profile is already connected to another account.
        try:
            TwitterProfile.objects.get(twitter_user_id=twitter_create['twitter_user_id'])
            proceed = False
            messages.error(request, _("Twitter profile already connected to another account."))
        except ObjectDoesNotExist:
            pass
        
        # Check if account exists with given email address.
        try:
            get_user_model().objects.get(email=email)
            proceed = False
            messages.error(request, _("Email already registered."))
        except ObjectDoesNotExist:
            pass
        
        #
        # Everything checks! \o/
        #
        if proceed:
            
            # 1) Create user with random password.
            try:
                random_password = generate_key(email + str(datetime.datetime.now()) + str(twitter_create['twitter_user_id']))
                random_password += datetime.datetime.now().strftime('%s')
                user = get_user_model().new(name=twitter_create['name'], email=email, password=random_password, credentials_type='twitter')
            except:
                logger.error('Error creating user via Twitter! #5 ' + str(twitter_create), exc_info=1)
                messages.error(request, _('Twitter login error #5'))
            
            # 2) Create Twitter profile and associate it with the new user.
            try:
                userinfo = UserInfo(twitter_user_id=twitter_create['twitter_user_id'], screen_name=twitter_create['screen_name'])
                TwitterProfile.new(user=user, userinfo=userinfo, access_token=twitter_create['access_token'])
                # Redirect to login page with message.
                messages.success(request, _("An email was sent in order to confirm your account."))
                return HttpResponseRedirect(reverse('yaccounts:login'))
            except:
                user.delete() # Delete newly created user (as it would be inaccessible since the Twitter Profile wasn't created!)
                logger.error('Error creating user via Twitter! #6 ' + str(twitter_create), exc_info=1)
                messages.error(request, _('Twitter login error #6'))
    
    # Render page.
    return render_to_response('yaccounts/create_social.html',
                              { 'avatar': twitter_create['profile_image_url'],
                               'username': '@' + twitter_create['screen_name'],
                               'email': email,
                               'post_url': reverse('yaccounts:twitter_create') },
                              context_instance=RequestContext(request))
    
    
@login_required
def disconnect_account(request):
    """
    Disconnects Twitter profile from user account.
    """
    
    # Check if user has a Twitter profile connected.
    if not hasattr(request.user, 'twitterprofile'):
        messages.error(request, _("You don't have a Twitter account connected."))
    
    # Disconnect!
    else:
        request.user.twitterprofile.delete()
        messages.success(request, _("Twitter account disconnected."))
    
    # Redirect to account page.
    return HttpResponseRedirect(reverse('yaccounts:index'))