import cgi
import datetime
import facebook
import logging
import random
import sha
import urllib
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.core.validators import validate_email
from django.db.utils import IntegrityError
from django.http.response import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.translation import ugettext as _

from models import FacebookProfile
import json

# Instantiate logger.
logger = logging.getLogger(__name__)

# Application's OAuth settings.
app_id = settings.YACCOUNTS['facebook_oauth']['app_id']
app_secret = settings.YACCOUNTS['facebook_oauth']['app_secret']

# Facebook OAuth URLs.
authorize_url = 'https://graph.facebook.com/oauth/authorize'
access_token_url = 'https://graph.facebook.com/oauth/access_token'


class UserInfo:
    """
    Facebook API userinfo object wrapper.
    """
    def __init__(self, userinfo):
        self.id = userinfo['id']
        self.name = userinfo['name']


def login_request(request):
    """
    Starts Facebook authentication.
    """
    
    # Check if Facebook authentication is enabled.
    try:
        settings.YACCOUNTS['signup_available'].index('FACEBOOK')
    except ValueError:
        messages.add_message(request, messages.ERROR, _('Facebook login not available.'))
        return HttpResponseRedirect(reverse('accounts:index'))
    
    # If there is an URL to return when login finishes,
    # store it in session in order to make it acessible in
    # the facebook return method (would be better to pass it in the URLs?)
    request.session['login_next'] = request.GET.get('next', reverse('accounts:index'))
    
    # Start authentication redirecting to respective page.
    return HttpResponseRedirect(authorize_url + '?client_id=' + app_id + '&redirect_uri=' + settings.HOST_URL + reverse('accounts:facebook_return'))


def login_return(request):
    """
    OAuth callback.
    """
    
    ##################
    # 1) Validations #
    ##################
    
    # Check for required parameter.
    code = request.GET.get('code', None)
    if not code:
        messages.add_message(request, messages.ERROR, _('Facebook login error #1'))
        return HttpResponseRedirect(reverse('accounts:index'))
    
    ###########################
    # 2) Request access token #
    ###########################
        
    request_access_token_url = access_token_url + '?client_id=' + app_id \
                                 + '&redirect_uri=' + settings.HOST_URL + reverse('accounts:facebook_return') \
                                 + '&client_secret=' + app_secret \
                                 + '&code=' + code
    response = cgi.parse_qs(urllib.urlopen(request_access_token_url).read())
    try:
        access_token = response['access_token'][-1]
    except KeyError:
        messages.add_message(request, messages.ERROR, _('Facebook login error #2'))
        return HttpResponseRedirect(reverse('accounts:index'))
    
    # Verify credentials.
    # Validate user access token. If we can fetch it's information, the token is good!
    try:
        fb_api = facebook.GraphAPI(access_token=access_token)
        userinfo = UserInfo(fb_api.get_object('me'))
    except:
        messages.add_message(request, messages.ERROR, _('Facebook login error #3'))
        return HttpResponseRedirect(reverse('accounts:index'))
    
    #########################################################
    # 3) Authenticate user with given Facebook credentials. #
    #########################################################
    user = authenticate(facebook_userinfo=userinfo, facebook_access_token=access_token)
    
    ##
    # a) Facebook profile is linked with existing user account.
    if user:
        
        # If user is active, login account and redirect to next page (if provided, else account profile)
        if user.is_active:
            login(request, user)
            return HttpResponseRedirect(request.session.get('login_next', reverse('accounts:index')))
        
        # User account is inactive.
        else:
            messages.warning(request, _("Your account is disabled."))
            return HttpResponseRedirect(reverse('accounts:login'))
        
    ##
    # b) Unknown Facebook profile.
    else:
        
        # i) If there is an account logged in, (attempt to) link the Facebook profile with it.
        if request.user.is_authenticated():
            try:
                FacebookProfile.new(user=request.user, userinfo=userinfo, access_token=access_token)
                messages.success(request, _("Facebook account connected successfully."))
            except IntegrityError:
                messages.error(request, _("You already have a Facebook profile linked to your account."))
            return HttpResponseRedirect(reverse('accounts:index'))
        
        # ii) Create new account.
        else:
            # Place Facebook info in a session variable in order for it to be accessed in the registration page.
            request.session['facebook_create'] = {
                    'facebook_user_id': userinfo.id,
                    'name': userinfo.name,
                    'profile_image_url': FacebookProfile.get_profile_image_url(userinfo.id),
                    'access_token': access_token,
                    'expires': (datetime.datetime.now() + datetime.timedelta(seconds=5*60)).strftime('%s') # Convert to epoch to be JSON serializable.
            }
            return HttpResponseRedirect(reverse('accounts:facebook_create'))
        
        
def create_account(request):
    """
    Create new account with Facebook credentials.
    """
    
    #
    # Lets validate if we should be here.
    #
    
    # If user is authenticated, then this place shouldn't be reached.
    # Facebook profile, if valid, should be linked with the logged in account and not create a new account.
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('accounts:index'))
    
    # In order to create account with Facebook profile, its details should have been stored in session.
    facebook_create = request.session.get('facebook_create', None)
    if not facebook_create:
        messages.error(request, _('Facebook login error #4'))
        return HttpResponseRedirect(reverse('accounts:login'))
    
    # If time window for registration of new account with this Facebook profile has expired,
    # delete it from session and restart Facebook login process.
    if datetime.datetime.now() > datetime.datetime.fromtimestamp(float(facebook_create['expires'])):
        del request.session['facebook_create']
        return HttpResponseRedirect(reverse('accounts:facebook_login'))
    
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
            
        # Check if Facebook profile is already connected to another account.
        try:
            FacebookProfile.objects.get(facebook_user_id=facebook_create['facebook_user_id'])
            proceed = False
            messages.error(request, _("Facebook profile already connected to another account."))
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
            
            # Create user with random password.
            try:
                
                # Generate random password.
                random_password = sha.new(sha.new(str(random.random())).hexdigest() \
                                          + email \
                                          + str(datetime.datetime.now())).hexdigest() \
                                          + str(facebook_create['facebook_user_id']) \
                                          + datetime.datetime.now().strftime('%s')
                
                # New user.
                user = get_user_model().new(name=facebook_create['name'],
                                            email=email,
                                            password=random_password)
                
                # Facebook profile.
                facebook_profile = FacebookProfile(user=user,
                                                  facebook_user_id=facebook_create['facebook_user_id'],
                                                  name=facebook_create['name'],
                                                  access_token=facebook_create['access_token'])
                facebook_profile.save()

                # Redirect to login page with message.
                messages.success(request, _("An email was sent in order to confirm your account."))
                return HttpResponseRedirect(reverse('accounts:login'))

            # Error creating new user.
            except:
                logger.error('Error creating user via Facebook! ' + str(facebook_create), exc_info=1)
                messages.error(request, _('Facebook login error #5'))
    
    # Render page.
    return render_to_response('yaccounts/create_social.html',
                              { 'avatar': facebook_create['profile_image_url'],
                               'username': facebook_create['name'],
                               'email': email,
                               'post_url': reverse('accounts:facebook_create') },
                              context_instance=RequestContext(request))
    
    
@login_required
def disconnect_account(request):
    """
    Disconnects Facebook profile from user account.
    """
    
    # Check if user has a Facebook profile connected.
    if not hasattr(request.user, 'facebookprofile'):
        messages.error(request, _("You don't have a Facebook account connected."))
    
    # Disconnect!
    else:
        request.user.facebookprofile.delete()
        messages.success(request, _("Facebook account disconnected."))
    
    # Redirect to account page.
    return HttpResponseRedirect(reverse('accounts:index'))