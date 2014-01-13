import base64
import json
import logging
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http.response import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from exceptions import InvalidParameter
from models import AuthenticationLog

# Instantiate logger.
logger = logging.getLogger(__name__)


@login_required
def index(request):
    """
    Account index.
    """
    # If user has photo.
    if hasattr(request.user, 'userphoto'):
        photo_url = request.user.userphoto.file.url
    else:
        photo_url = None
    
    # Render page.
    return render_to_response('accounts/index.html',
                              { 'name': request.user.name,
                                'email': request.user.email,
                                'photo_url': photo_url,
                                'change_photo_url': settings.HOST_URL + reverse('api:v1:accounts:photo') },
                              context_instance=RequestContext(request))


def login_account(request):
    """
    Login account.
    """
    # If a user is logged in, redirect to account page.
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('accounts:index'))
    
    ################################################################
    #                     A form was submitted.                    #
    ################################################################
    if request.method == 'POST':
        
        # Additional information on the request that should be logged.
        metadata = { 'user_agent': request.META['HTTP_USER_AGENT'] }
        
        #
        # 1) Fetch params.
        #
        email = request.POST.get('email', '')
        password = request.POST.get('password', '')
        remember = request.POST.get('remember', None)
        
        # Mandatory parameters not provided.
        if email == '' or password == '':
            # Message.
            messages.error(request, _("Please provide your email and password."))
        
        #
        # 2) Validate credentials.
        #
        else:
            
            user = authenticate(email=email, password=password)
            
            ######################
            # VALID credentials. #
            ######################
            if user is not None:
                
                #
                # a) Account is ACTIVE.
                #
                if user.is_active:
                    
                    # Login user.
                    login(request, user)
                    
                    # If NOT flaged to remember.
                    if not remember: 
                        request.session.set_expiry(0)
                        
                    # Log authentication.
                    AuthenticationLog.new(email=email,
                                          valid_credentials=True,
                                          account_status='active',
                                          success=True,
                                          ip_address=request.META['REMOTE_ADDR'],
                                          metadata=json.dumps(metadata))
                    
                    #
                    # *** If login successful, REDIRECT to profile page or to provided url. ***
                    #
                    return HttpResponseRedirect(request.POST.get('next', reverse('accounts:index')))
                
                #
                # b) Account is PENDING ACTIVATION.
                #
                elif user.pending_activation():
                    
                    # Log authentication.
                    AuthenticationLog.new(email=email,
                                          valid_credentials=True,
                                          account_status='pending_activation',
                                          success=False,
                                          ip_address=request.META['REMOTE_ADDR'],
                                          metadata=json.dumps(metadata))
                    
                    # Message.
                    messages.warning(request, mark_safe(_("You didn't activate your account. <a href=\"\">Resend confirmation email</a>.")))
                
                #
                # c) Account is DISABLED.
                #
                else:
                    
                    # Log authentication.
                    AuthenticationLog.new(email=email,
                                          valid_credentials=True,
                                          account_status='disabled',
                                          success=False,
                                          ip_address=request.META['REMOTE_ADDR'],
                                          metadata=json.dumps(metadata))
                    
                    # Message.
                    messages.warning(request, _("Your account is disabled."))
            
            ########################
            # INVALID credentials. #
            ########################
            else:
                
                # Check if account with given email address exists.
                try:
                    user = get_user_model().objects.get(email=email)
                    # Account exists, check status.
                    if user.is_active:
                        account_status = 'active'
                    elif user.pending_activation():
                        account_status = 'pending_activation'
                    else:
                        account_status = 'disabled'
                # There is no account with given email address.
                except ObjectDoesNotExist:
                    account_status = 'does_not_exist'
                
                # Log authentication.
                AuthenticationLog.new(email=email,
                                      valid_credentials=False,
                                      account_status=account_status,
                                      success=False,
                                      ip_address=request.META['REMOTE_ADDR'],
                                      metadata=json.dumps(metadata))
                
                # Message.
                messages.error(request, _("Invalid credentials."))
        
        #
        # 3) If this place is reached, then login was unsuccessful.
        # The login page is rendered with respective message and pre-filled fields.
        #
        return render_to_response('accounts/login.html',
                                  { 'email': email, 'next': request.POST.get('next', None) },
                                  context_instance=RequestContext(request))
    
    ################################################################
    #                      Render login page.                      #
    ################################################################
    else:
        return render_to_response('accounts/login.html',
                                  { 'next': request.GET.get('next', None) },
                                  context_instance=RequestContext(request))


def logout_account(request):
    """
    Logout.
    """
    if request.user.is_authenticated():
        logout(request)
    return HttpResponseRedirect(request.GET.get('next', reverse('accounts:index')))


def create_account(request):
    """
    Creates a new account.
    """
    # Check if this feature is enabled.
    if not settings.ACCOUNT_CREATION_AVAILABLE:
        raise Http404
    
    # If a user is logged in, redirect to account page.
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('accounts:index'))
    
    ################################################################
    #                     A form was submitted.                    #
    ################################################################
    if request.method == 'POST':
        
        #
        # 1) Fetch params.
        #
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        password = request.POST.get('password', '')
        
        # Mandatory parameters not provided.
        if name == '' or email == '' or password == '':
            messages.error(request, _("Please provide your name, email and a password."))
        
        #
        # 2) Create account.
        #
        else:
            
            # If all parameters check, then a new account is created.
            try:
                get_user_model().new(name=name, email=email, password=password)
                messages.success(request, _("An email was sent in order to confirm your account."))
                return HttpResponseRedirect(reverse('accounts:login'))
            
            # Invalid parameters.
            except InvalidParameter as e:
                messages.error(request, e.message)    
            
            # Unknown error.
            except:
                messages.error(request, _("Error creating account, please contact support."))
        
        #
        # 3) If this place is reached, then account creation form contained errors.
        # The sign-up page is rendered with respective message and pre-filled fields.
        #
        return render_to_response('accounts/create.html',
                                  { 'name': name, 'email': email, 'next': request.POST.get('next', None) },
                                  context_instance=RequestContext(request))
    
    ################################################################
    #                     Render sign-up page.                     #
    ################################################################
    else:
        return render_to_response('accounts/create.html',
                                  { 'next': request.GET.get('next', None) },
                                  context_instance=RequestContext(request))


def confirm_account(request):
    """
    Confirm email address for account activation or email address update.
    """
    #
    # Fetch token.
    #
    try:
        token = request.GET['t']
        if token == '':
            raise KeyError
    except KeyError:
        raise Http404
    
    #
    # Process token.
    #
    try:
        
        # A valid token is a base64 encoded string.
        confirm_data = json.loads(base64.b64decode(token))
        
        # Containing the account's email, confirmation scenario and respective key.
        try:
            email = confirm_data['email']
            operation = confirm_data['operation']
            key = confirm_data['key']
        except KeyError:
            logger.info('Invalid account confirmation DATA! Data: ' + json.dumps(confirm_data) + ', IP Address: ' + request.META['REMOTE_ADDR'])
            raise Http404
    
    # Unable to b64 decode.
    except TypeError:
        logger.info('Invalid BASE64 account confirmation token! Token: ' + token + ', IP Address: ' +  request.META['REMOTE_ADDR'])
        raise Http404
    
    # Error decoding JSON
    except ValueError:
        logger.info('Invalid JSON account confirmation token! Token: ' + token + ', IP Address: ' +  request.META['REMOTE_ADDR'])
        raise Http404
    
    #
    # Validate operation.
    #
    if operation == 'activation':
        
        # Verify activation key, by attempting to authenticate user using it.
        user = authenticate(email=email, activation_key=key)
        
        # If a user is returned, then the activation key checked out and the account activated.
        if user is not None:
            
            # Login user.
            login(request, user)
            
            # Redirect to account page.
            return HttpResponseRedirect(reverse('accounts:index'))
            
        # Invalid activation key.
        else:
            logger.info('Invalid activation key! Data: ' + json.dumps(confirm_data) + ', IP Address: ' + request.META['REMOTE_ADDR'])
            raise Http404
    
    # Invalid operation.
    else:
        logger.info('Invalid account confirmation OPERATION! Data: ' + json.dumps(confirm_data) + ', IP Address: ' + request.META['REMOTE_ADDR'])
        raise Http404