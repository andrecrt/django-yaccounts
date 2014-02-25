import datetime
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
from models import AuthenticationLog, ResetRequest, EmailUpdate
from utils import ConfirmationToken

# Instantiate logger.
logger = logging.getLogger(__name__)


@login_required
def index(request):
    """
    Account index.
    """
        
    # If user has Twitter profile.
    if hasattr(request.user, 'twitterprofile'):
        twitter_profile = request.user.twitterprofile
    else:
        twitter_profile = None
        
    # If user has Facebook profile.
    if hasattr(request.user, 'facebookprofile'):
        facebook_profile = request.user.facebookprofile
    else:
        facebook_profile = None
    
    # Render page.
    return render_to_response('yaccounts/index.html',
                              { 'name': request.user.name,
                                'email': request.user.email,
                                'photo_url': request.user.get_photo_url(),
                                'photo_update_api_url': settings.HOST_URL + reverse(settings.YACCOUNTS['api_url_namespace'] + ':yaccounts:photo'),
                                'account_update_api_url': settings.HOST_URL + reverse(settings.YACCOUNTS['api_url_namespace'] + ':yaccounts:index'),
                                'api_keys_api_url': settings.HOST_URL + reverse(settings.YACCOUNTS['api_url_namespace'] + ':yaccounts:api_keys'),
                                'twitter_profile': twitter_profile, 'facebook_profile': facebook_profile },
                              context_instance=RequestContext(request))


def login_account(request):
    """
    Login account.
    """
    # If a user is logged in, redirect to account page.
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('yaccounts:index'))
    
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
                                          credentials_type='email',
                                          account_status='active',
                                          success=True,
                                          ip_address=request.META['REMOTE_ADDR'],
                                          metadata=json.dumps(metadata))
                    
                    #
                    # *** If login successful, REDIRECT to profile page or to provided url. ***
                    #
                    return HttpResponseRedirect(request.POST.get('next', reverse('yaccounts:index')))
                
                #
                # b) Account is PENDING ACTIVATION.
                #
                elif user.pending_activation():
                    
                    # Log authentication.
                    AuthenticationLog.new(email=email,
                                          valid_credentials=True,
                                          credentials_type='email',
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
                                          credentials_type='email',
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
                                      credentials_type='email',
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
        return render_to_response('yaccounts/login.html',
                                  { 'email': email, 'next': request.POST.get('next', None) },
                                  context_instance=RequestContext(request))
    
    ################################################################
    #                      Render login page.                      #
    ################################################################
    else:
        return render_to_response('yaccounts/login.html',
                                  { 'next': request.GET.get('next', None) },
                                  context_instance=RequestContext(request))


def logout_account(request):
    """
    Logout.
    """
    if request.user.is_authenticated():
        logout(request)
    return HttpResponseRedirect(request.GET.get('next', reverse('yaccounts:index')))


def create_account(request):
    """
    Creates a new account.
    """
    # If a user is logged in, redirect to account page.
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('yaccounts:index'))
    
    ################################################################
    #                     A form was submitted.                    #
    ################################################################
    if request.method == 'POST':
        
        # Check if this feature is enabled.
        try:
            settings.YACCOUNTS['signup_available'].index('EMAIL')
        except:
            raise Http404
        
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
                get_user_model().new(name=name,
                                     email=email,
                                     password=password,
                                     credentials_type='email')
                messages.success(request, _("An email was sent in order to confirm your account."))
                return HttpResponseRedirect(reverse('yaccounts:login'))
            
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
        return render_to_response('yaccounts/create.html',
                                  { 'name': name, 'email': email, 'next': request.POST.get('next', None) },
                                  context_instance=RequestContext(request))
    
    ################################################################
    #                     Render sign-up page.                     #
    ################################################################
    else:
        return render_to_response('yaccounts/create.html',
                                  { 'next': request.GET.get('next', None) },
                                  context_instance=RequestContext(request))


def confirm_operation(request):
    """
    Confirm operation (e.g. Account activation, email change, etc)
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
    processed_token = ConfirmationToken.process(token)
    
    # Invalid token.
    if not processed_token:
        raise Http404
    
    # Token info.
    else:
        operation = processed_token['operation']
        email = processed_token['email']
        key = processed_token['key']
    
    #
    # Validate operation.
    #
    
    ## Account activation.
    #
    if operation == ConfirmationToken.ACCOUNT_ACTIVATION:
        
        # Verify activation key, by attempting to authenticate user using it.
        user = authenticate(email=email, activation_key=key)
        
        # If a user is returned, then the activation key checked out and the account activated.
        if user is not None:
            
            # Login user.
            login(request, user)
            
            # Redirect to account page.
            return HttpResponseRedirect(reverse('yaccounts:index'))
            
        # Invalid activation key.
        else:
            logger.info('Invalid activation key! Data: ' + str(processed_token) + ', IP Address: ' + request.META['REMOTE_ADDR'])
            raise Http404
        
    ## Email update.
    #
    elif operation == ConfirmationToken.ACCOUNT_EMAIL_UPDATE:
        
        # Fetch additional required params.
        try:
            new_email = processed_token['new_email']
        except KeyError:
            logger.error('Error updating email! Missing new_email. Data: ' + str(processed_token) + ', IP Address: ' + request.META['REMOTE_ADDR'])
            raise Http404
        
        # Check if user with given email exists.
        try:
            user = get_user_model().objects.get(email=email)
        except ObjectDoesNotExist:
            logger.error('Error updating email! User does not exist. Data: ' + str(processed_token) + ', IP Address: ' + request.META['REMOTE_ADDR'])
            raise Http404
        
        # Check if there is a pending update request for the user->email->key.
        email_update = EmailUpdate.objects.filter(user=user, new_email=new_email, key=key, updated_at__isnull=True)
        if not email_update:
            logger.error('Error updating email! No pending update for given details. Data: ' + str(processed_token) + ', IP Address: ' + request.META['REMOTE_ADDR'])
            raise Http404
        
        # GREAT SUCCESS!
        else:
            
            # Update email.
            user.update(email=new_email)
            
            # Mark key as used.
            for update in email_update:
                update.updated_at = datetime.datetime.now()
                update.save()
            
            # Message.
            messages.success(request, _("Your new email was confirmed."))
            
            # Redirect to account page.
            return HttpResponseRedirect(reverse('yaccounts:index'))
    
    ## Invalid operation.
    #
    else:
        logger.error('Invalid account confirmation OPERATION! Data: ' + str(processed_token) + ', IP Address: ' + request.META['REMOTE_ADDR'])
        raise Http404


def reset_account(request):
    """
    Request password reset.
    """
    
    email = ''
    
    # A reset was requested.
    if request.method == 'POST':
        
        # Mandatory params.
        email = request.POST.get('email', '')
        if email == '':
            messages.error(request, _("Please provide your email."))
        
        # Business as usual...
        else:
            # Check if user with given email exists.
            try:
                user = get_user_model().objects.get(email=email)
                
                # Check if account is active.
                if not user.is_active:
                    messages.error(request, _("Your account is disabled."))
                
                #
                # If this place is reached, then we have a valid account. Proceed with reset request! ------------->
                #
                
                # Check if a password reset for this user wasn't requested less than 5 mins ago.
                elif ResetRequest.objects.filter(user=user,
                                               created_at__gte=(datetime.datetime.now() - datetime.timedelta(0, 300))):
                    messages.error(request, _("A reset was requested recently."))
                    
                # Send reset email.
                else:
                    try:
                        ResetRequest.new(user)
                        email = ''
                        messages.success(request, _("An email was sent with reset instructions."))
                    except:
                        logger.error('Unable to reset password! Email: ' + email, exc_info=1)
                        messages.error(request, _("Unable to reset password."))
                
                #
                # <-------------------------------------------------------------------------------------------------
                #
                
            except ObjectDoesNotExist:
                messages.error(request, _("User does not exist."))
    
    # Render page.
    return render_to_response('yaccounts/reset.html',
                              { 'email': email },
                              context_instance=RequestContext(request))
    

def reset_confirm(request):
    """
    If token is valid, allow password change.
    """
    
    #
    # Process token.
    #
    try:
        token = request.GET['t']
        processed_token = ConfirmationToken.process(token)
    except KeyError:
        raise Http404
    
    # Invalid token.
    if not processed_token:
        raise Http404
    
    # Token info.
    else:
        operation = processed_token['operation']
        email = processed_token['email']
        key = processed_token['key']
        
    #
    # Validate email.
    #
    try:
        user = get_user_model().objects.get(email=email)
    except ObjectDoesNotExist:
        logger.warning('Valid reset token for an invalid user! Email: ' + email + ', Key: ' + key + ', Operation: '+ operation + ', IP Address: ' + request.META['REMOTE_ADDR'])
        raise Http404
    
    #
    # Validate operation.
    #
    if operation == ConfirmationToken.ACCOUNT_PASSWORD_RESET:
        
        # Check if an unused reset key exists.
        try:
            reset_request = ResetRequest.objects.get(user=user, key=key, reset_at__isnull=True)
        except ObjectDoesNotExist:
            logger.debug('Invalid reset key! Email: ' + email + ', Key: ' + key)
            raise Http404
        
        # A password update was requested.
        if request.method == 'POST':
            
            # Mandatory params.
            password = request.POST.get('password', '')
            password_confirm = request.POST.get('password_confirm', '')
            if password == '' or password_confirm == '':
                messages.error(request, _("Please provide a password and respective confirmation."))
                
            # Check if new password and confirmation match.
            elif password != password_confirm:
                messages.error(request, _("Passwords don't match."))
        
            # Proceed with reset!
            else:
                
                # Mark key as used.
                reset_request.reset_at = datetime.datetime.now()
                reset_request.save()
                
                # Update user's password.
                reset_request.user.update(password=password)
                
                # Login user.
                user = authenticate(email=email, password=password)
                login(request, user)
                
                # Redirect to account page.
                messages.success(request, _("Your password was updated."))
                return HttpResponseRedirect(reverse('yaccounts:index'))
        
        # Render page.
        return render_to_response('yaccounts/reset_confirm.html',
                                  { 'token': token },
                                  context_instance=RequestContext(request))
    
    # Invalid operation.
    else:
        logger.info('Invalid reset confirmation OPERATION! Email: ' + email + ', Key: ' + key + ', Operation: ' + operation + ', IP Address: ' + request.META['REMOTE_ADDR'])
        raise Http404
    