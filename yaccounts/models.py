import Image
import logging
import os
import re
import tempfile
import twitter
import urllib2
from django.db import models
from django.conf import settings
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.core.urlresolvers import reverse
from django.core.validators import validate_email
from django.template import Context
from django.template.loader import get_template
from django.utils.translation import ugettext as _
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from yapi.utils import generate_key
from yutils.email import EmailMessage

from exceptions import InvalidParameter
from utils import ConfirmationToken
from django.core import files

# Instantiate logger.
logger = logging.getLogger(__name__)


# Supported user credentials for authentication.
CREDENTIAL_TYPES = (
    ('api', 'API'),
    ('email', 'E-mail'),
    ('facebook', 'Facebook'),
    ('twitter', 'Twitter')
)


class UserManager(BaseUserManager):
    """
    Since the custom User model defines different fields than Django's default, this custom
    manager must be implemented.
    """
    
    def create_user(self, name, email, password=None):
        """
        Creates and saves a User.
        """
        user = self.model(name=name, email=email)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, name, email, password):
        """
        Creates and saves a superuser.
        """
        user = self.create_user(name, email, password=password)
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.save()
        return user


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model.
    """    
    # Fields.
    email = models.EmailField(verbose_name=_("Email address"), max_length=100, unique=True, db_index=True)
    name = models.CharField(verbose_name=_("Name"), max_length=100)
    is_active = models.BooleanField(verbose_name=_("Active"), help_text=_("Designates whether this user should be treated as active. Unselect this instead of deleting accounts."), default=False)
    is_staff = models.BooleanField(verbose_name=_("Staff status"), help_text=_("Designates whether the user can log into this admin site."), default=False)
    created_at = models.DateTimeField(verbose_name=_("Created at"), auto_now_add=True)
    created_via = models.CharField(max_length=20, choices=CREDENTIAL_TYPES, blank=True)

    # Required for custom User models.
    objects = UserManager()

    # The name of the field on the User model that is used as the unique identifier.
    USERNAME_FIELD = 'email'
    
    # A list of the field names that must be provided when creating a user via the createsuperuser management command.
    REQUIRED_FIELDS = ['name']

    def get_full_name(self):
        """
        A longer formal identifier for the user.
        """
        return self.name

    def get_short_name(self):
        """
        A short, informal identifier for the user.
        """
        return self.name

    def __unicode__(self):
        """
        String representation of the model instance.
        """
        return self.email
    
    def pending_activation(self):
        """
        Returns whether the account is pending authentication or not.
        """
        # The account is considered to be pending authentication if there is an
        # 'unused' activation key.
        try:
            ActivationKey.objects.get(user=self, activated_at__isnull=True)
            return True
        except ObjectDoesNotExist:
            return False
        
    @staticmethod
    def new(name, email, password, credentials_type, email_activation_key=True):
        """
        Creates a new account.
        """
        # Validate email address.
        try:
            validate_email(email)
        except ValidationError:
            raise InvalidParameter('email', _("Please provide a valid email address"))
        
        # Check if account with given email already exists.
        try:
            User.objects.get(email=email)
            # If this place is reached, then account with given email already exists. Abort.
            raise InvalidParameter('email', _("This email is already registered."))
        except ObjectDoesNotExist:
            pass
        
        # All check, create account.
        user = User.objects.create_user(name=name, email=email, password=password)
        user.created_via = credentials_type
        user.save()
        
        # Create activation key.
        try:
            ActivationKey.new(user, email_activation_key)
        
        # Unable to create activation key, abort account creation.
        except:
            logger.error('Unable to create activation key! Name: ' + name + ', Email: ' + email, exc_info=1)
            user.delete()
            raise
        
        # Return.
        return user
    
    def update(self, name=None, password=None, email=None):
        """
        Update user account.
        """
        if name and name != '':
            self.name = name
        if password and password != '':
            self.set_password(password)
        if email and email != '':
            self.email = email
        self.save()
        
    def get_photo_url(self):
        """
        Returns the account's photo URL.
        """
        # If user has set a photo.
        if hasattr(self, 'userphoto'):
            photo_url = self.userphoto.file.url
    
        # Else, return default avatar.
        else:
            photo_url = settings.HOST_URL + settings.STATIC_URL + 'yaccounts/images/avatar_default.png'
            
        # Return.
        return photo_url
    
    def set_photo(self, photo_file, filename=None):
        """
        Sets the account photo.
        """    
        # 1) If user has photo, delete old file.
        if hasattr(self, 'userphoto'):
            user_photo = self.userphoto
            os.remove(user_photo.file.path)
        # If not, create it.
        else:
            user_photo = UserPhoto(user=self)
            
        # 2) If a filename is provided, set it.
        if filename and filename != '':
            user_photo.file.save(filename, photo_file, save=False)
        # If not, just add photo.
        else:
            user_photo.file = photo_file
            
        # 3) Save.
        user_photo.save()
        
        # 4) Resize image. User photos are fixed to 140x140.
        try:
            im = Image.open(user_photo.file.path)
            im = im.resize((140, 140), Image.ANTIALIAS)
            im.save(user_photo.file.path, format='JPEG')
        except IOError:
            user_photo.destroy() # In order to not get stuck with an invalid image and, therefore, a nasty icon in the browser :P
            logger.error('Error resizing user photo! User: ' + str(self.email), exc_info=1)
            raise
        
        # 5) Return.
        return user_photo
    
    def set_photo_from_url(self, image_url, filename=None):
        """
        Fetches file from given URL and sets it as the account's photo.
        """
        # Fetch file from URL.
        response = urllib2.urlopen(image_url)
        
        # Create a temporary file.
        lf = tempfile.NamedTemporaryFile()
        lf.write(response.read())
        
        # If no filename is provided, make it the last part of the URL.
        if not filename or filename == '':
            name = image_url.split('/')[-1]
        else:
            name = filename
        
        # Set the account photo.
        self.set_photo(photo_file=files.File(lf), filename=name)


class UserPhoto(models.Model):
    """
    User profile picture.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL)
    file = models.ImageField(upload_to='yaccounts/profile_pictures/')
    
    def __unicode__(self):
        """
        String representation of the instance.
        """
        return str(self.user)
    
    def destroy(self):
        """
        Deletes instance AND file.
        """
        os.remove(self.file.path)
        self.delete()


class ActivationKey(models.Model):
    """
    Keys used to activate new accounts.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL)
    key = models.CharField(max_length=200, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(blank=True, null=True)
    
    def __unicode__(self):
        """
        String representation of the model instance.
        """
        return str(self.user)
    
    @staticmethod
    def new(user, email_activation_key):
        """
        Creates an activation key for given user.
        """
        activation_key = ActivationKey(user=user, key=generate_key(salt=user.email))
        activation_key.save()
        if email_activation_key:
            activation_key.send_activation_link()
        return True
    
    def send_activation_link(self):
        """
        Sends the activation URL to the customers's email.
        """
        try:
            # Email variables.
            d = Context({
                'name': self.user.name,
                'activation_link': settings.HOST_URL + reverse('yaccounts:confirm') + '?t=' + ConfirmationToken.generate(self.user.email, ConfirmationToken.ACCOUNT_ACTIVATION, self.key)
            })
            
            # Render plaintext email template.
            plaintext = get_template('yaccounts/email/create_confirmation.txt')
            text_content = plaintext.render(d)
            
            # Render HTML email template.
            html = get_template('yaccounts/email/create_confirmation.html')
            html_content = html.render(d)
            
            # Email options.
            subject = _("New Account")
            from_email = settings.YACCOUNTS['email_from']
            to = [{ 'name': self.user.name, 'email': self.user.email }]
            
            # Build message and send.
            email = EmailMessage(sender=from_email,
                                recipients=to,
                                subject=subject,
                                text_content=text_content,
                                html_content=html_content,
                                tags=['Account Confirm'])
            result = email.send()
            
            # Check if email wasn't sent.
            if not result['sent']:
                logger.error('Account Confirmation Email Not Sent! Result: ' + str(result['result']))
                raise
        except:
            logger.error('Unable to send confirmation email', exc_info=1)
            raise
        
        # Return great success.
        return True


class AuthenticationLog(models.Model):
    """
    Logs successful and failed logins.
    """
    # Available account statuses.
    ACCOUNT_STATUS = (
        ('active', 'Active'),
        ('disabled', 'Disabled'),
        ('does_not_exist', 'Does Not Exist'),
        ('pending_activation', 'Pending Activation')
    )
    
    # Fields.
    date = models.DateTimeField(auto_now_add=True)
    email = models.CharField(max_length=100)
    valid_credentials = models.BooleanField(default=False)
    credentials_type = models.CharField(max_length=20, choices=CREDENTIAL_TYPES, blank=True)
    account_status = models.CharField(max_length=20, choices=ACCOUNT_STATUS)
    success = models.BooleanField(default=False)
    ip_address = models.CharField(max_length=50)
    metadata = models.TextField(blank=True) # Additional data on the subject.
    
    def __unicode__(self):
        """
        String representation of the model instance.
        """
        return self.email
    
    @staticmethod
    def new(email, valid_credentials, credentials_type, account_status, success, ip_address, metadata):
        """
        Logs an authentication event.
        """
        # Build authentication log.
        authlog = AuthenticationLog(email=email,
                                    valid_credentials=valid_credentials,
                                    credentials_type=credentials_type,
                                    account_status=account_status,
                                    success=success,
                                    ip_address=ip_address,
                                    metadata=metadata)
        
        # Shave and return.
        authlog.save()
        return authlog
    
    
class ResetRequest(models.Model):
    """
    Account password reset.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    key = models.CharField(max_length=200, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reset_at = models.DateTimeField(blank=True, null=True)
    
    def __unicode__(self):
        """
        String representation of the model instance.
        """
        return str(self.user)
    
    @staticmethod
    def new(user):
        """
        Creates an activation key for given user.
        """
        reset_request = ResetRequest(user=user, key=generate_key(salt=user.email))
        reset_request.save()
        try:
            reset_request.send_reset_link()
        except:
            reset_request.delete()
            raise
        return True
    
    def send_reset_link(self):
        """
        Sends the reset URL to the customers's email.
        """
        try:
            # Email variables.
            d = Context({
                'name': self.user.name,
                'reset_link': settings.HOST_URL + reverse('yaccounts:reset_confirm') + '?t=' + ConfirmationToken.generate(self.user.email, ConfirmationToken.ACCOUNT_PASSWORD_RESET, self.key)
            })
            
            # Render plaintext email template.
            plaintext = get_template('yaccounts/email/reset_confirmation.txt')
            text_content = plaintext.render(d)
            
            # Render HTML email template.
            html = get_template('yaccounts/email/reset_confirmation.html')
            html_content = html.render(d)
            
            # Email options.
            subject = _("Reset Password")
            from_email = settings.YACCOUNTS['email_from']
            to = [{ 'name': self.user.name, 'email': self.user.email }]
            
            # Build message and send.
            email = EmailMessage(sender=from_email,
                                recipients=to,
                                subject=subject,
                                text_content=text_content,
                                html_content=html_content,
                                tags=['Account Reset'])
            result = email.send()
            
            # Check if email wasn't sent.
            if not result['sent']:
                logger.error('Password Reset Email Not Sent! Result: ' + str(result['result']))
                raise
        except:
            logger.error('Unable to send password reset email', exc_info=1)
            raise
        
        # Return great success.
        return True
    

class EmailUpdate(models.Model):
    """
    Account email update request/validation.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    old_email = models.EmailField()
    new_email = models.EmailField()
    key = models.CharField(max_length=200, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    
    def __unicode__(self):
        """
        String representation of the model instance.
        """
        return str(self.user)
    
    @staticmethod
    def new(user, email):
        """
        Creates an email update request for given user.
        """
        email_update = EmailUpdate(user=user, old_email=user.email, new_email=email, key=generate_key(salt=(str(user.email)+str(email))))
        email_update.save()
        try:
            email_update.send_confirmation_link()
        except:
            email_update.delete()
            raise
        return True
    
    def send_confirmation_link(self):
        """
        Sends the confirmation URL to the customers's email.
        """
        try:
            # Email variables.
            d = Context({
                'name': self.user.name,
                'confirmation_link': settings.HOST_URL + reverse('yaccounts:confirm') + '?t=' + ConfirmationToken.generate(email=self.user.email,
                                                                                                                          operation=ConfirmationToken.ACCOUNT_EMAIL_UPDATE,
                                                                                                                          key=self.key,
                                                                                                                          more={ 'new_email': self.new_email })
            })
            
            # Render plaintext email template.
            plaintext = get_template('yaccounts/email/email_update_confirmation.txt')
            text_content = plaintext.render(d)
            
            # Render HTML email template.
            html = get_template('yaccounts/email/email_update_confirmation.html')
            html_content = html.render(d)
            
            # Email options.
            subject = _("Confirm Email")
            from_email = settings.YACCOUNTS['email_from']
            to = [{ 'name': self.user.name, 'email': self.new_email }]
            
            # Build message and send.
            email = EmailMessage(sender=from_email,
                                recipients=to,
                                subject=subject,
                                text_content=text_content,
                                html_content=html_content,
                                tags=['Account Email Update'])
            result = email.send()
            
            # Check if email wasn't sent.
            if not result['sent']:
                logger.error('Email Update Confirmation Not Sent! Result: ' + str(result['result']))
                raise
        except:
            logger.error('Unable to send email confirmation update link', exc_info=1)
            raise
        
        # Return great success.
        return True
    
    
class TwitterProfile(models.Model):
    """
    Twitter profiles connected to user accounts.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL)
    twitter_user_id = models.CharField(max_length=200, unique=True, db_index=True)
    screen_name = models.CharField(max_length=50)
    access_token = models.CharField(max_length=200)
    access_token_secret = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(blank=True, null=True)
    
    def __unicode__(self):
        """
        String representation of the model instance.
        """
        return str(self.user)
    
    @staticmethod
    def new(user, userinfo, access_token):
        """
        Links a Twitter profile with account.
        """
        # Create Twitter profile.
        twitter_profile = TwitterProfile(user=user,
                                         twitter_user_id=userinfo.id,
                                         screen_name=userinfo.screen_name,
                                         access_token=access_token['oauth_token'],
                                         access_token_secret=access_token['oauth_token_secret'])
        twitter_profile.save()
        
        # If user's account doesn't have a photo, fetch Twitter profile's photo.
        if not hasattr(twitter_profile.user, 'userphoto'):
            twitter_profile.user.set_photo_from_url(twitter_profile.get_photo_url())
        
        # Return.
        return twitter_profile
    
    def update(self, userinfo, access_token):
        """
        Updates a user's Twitter profile.
        """
        self.screen_name = userinfo.screen_name
        self.access_token = access_token['oauth_token']
        self.access_token_secret = access_token['oauth_token_secret']
        self.save()
        return self
    
    def get_photo_url(self):
        """
        Returns the profile's photo url.
        """
        # Initialize API connector stuffz.
        api = twitter.Api(consumer_key=settings.YACCOUNTS['twitter_oauth']['consumer_key'],
                          consumer_secret=settings.YACCOUNTS['twitter_oauth']['consumer_secret'],
                          access_token_key=self.access_token,
                          access_token_secret=self.access_token_secret)
        
        # Get profile image URL from userinfo.
        image_url = api.VerifyCredentials().profile_image_url
        
        # Since we want the original size of the image, we have to change the filename in the URL, by removing '_normal'.
        splited_url = image_url.split('/')
        splited_url[-1] = re.sub('_normal', '', splited_url[-1])
        
        # Return 'updated' URL.
        return '/'.join(splited_url)
    
    
class FacebookProfile(models.Model):
    """
    Holds a user's Fakebook profile.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL)
    facebook_user_id = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=50)
    access_token = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(blank=True, null=True)

    def __unicode__(self):
        """
        String representation of the model instance.
        """
        return str(self.user)
    
    @staticmethod
    def new(user, userinfo, access_token):
        """
        Links a Facebook profile with account.
        """
        # Create Twitter profile.
        facebook_profile = FacebookProfile(user=user,
                                           facebook_user_id=userinfo.id,
                                           name=userinfo.name,
                                           access_token=access_token)
        facebook_profile.save()
        
        # If user's account doesn't have a photo, fetch Twitter profile's photo.
        if not hasattr(facebook_profile.user, 'userphoto'):
            facebook_profile.user.set_photo_from_url(image_url=facebook_profile.get_photo_url(), filename=str(facebook_profile.facebook_user_id) + '.png')
        
        # Return.
        return facebook_profile
    
    def update(self, userinfo, access_token):
        """
        Updates a user's Facebook profile.
        """
        self.name = userinfo.name
        self.access_token = access_token
        self.save()
        return self
    
    def get_photo_url(self):
        """
        Returns the profile's photo url.
        """
        return FacebookProfile.get_profile_image_url(self.facebook_user_id)
        
    @staticmethod
    def get_profile_image_url(fbid):
        """
        Returns the link to the profile image, given the user's Facebook ID.
        """
        return 'https://graph.facebook.com/' + fbid + '/picture?type=large'