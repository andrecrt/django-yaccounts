import base64
import json
import logging
from django.db import models
from django.conf import settings
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.core.urlresolvers import reverse
from django.core.validators import validate_email
from django.template import Context
from django.template.loader import get_template
from django.utils.translation import ugettext as _
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from exceptions import InvalidParameter
from yapi.utils import generate_key
from yutils.email import EmailMessage

# Instantiate logger.
logger = logging.getLogger(__name__)


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
    def new(name, email, password):
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
        
        # Create activation key.
        try:
            ActivationKey.new(user)
        
        # Unable to create activation key, abort account creation.
        except:
            logger.error('Unable to create activation key! Name: ' + name + ', Email: ' + email, exc_info=1)
            user.delete()
            raise
        
        # Return.
        return user
    
    def update(self, name=None, password=None):
        """
        Update user account.
        """
        if name and name != '':
            self.name = name
        if password and password != '':
            self.set_password(password)
        self.save()
    
    
class UserPhoto(models.Model):
    """
    User profile picture.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL)
    file = models.ImageField(upload_to='accounts/photos/')
    
    def __unicode__(self):
        """
        String representation of the instance.
        """
        return str(self.user)


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
    def new(user):
        """
        Creates an activation key for given user.
        """
        activation_key = ActivationKey(user=user, key=generate_key(salt=user.email))
        activation_key.save()
        activation_key.send_activation_link()
        return True
    
    def get_activation_token(self):
        """
        Returns a Base64 encoded string containing the account's email and activation key.
        """
        token = {
            'email': self.user.email,
            'operation': 'activation',
            'key': self.key
        }
        return base64.b64encode(json.dumps(token))
    
    def send_activation_link(self):
        """
        Sends the activation URL to the customers's email.
        """
        try:
            # Email variables.
            d = Context({
                'name': self.user.name,
                'activation_link': settings.HOST_URL + reverse('accounts:confirm') + '?t=' + self.get_activation_token()
            })
            
            # Render plaintext email template.
            plaintext = get_template('accounts/email/create_confirmation.txt')
            text_content = plaintext.render(d)
            
            # Render HTML email template.
            html = get_template('accounts/email/create_confirmation.html')
            html_content = html.render(d)
            
            # Email options.
            subject = _("New Account")
            from_email = settings.ACCOUNT_CREATION_MAIL_SENDER
            to = [{ 'name': self.user.name, 'email': self.user.email }]
            
            # Build message and send.
            email = EmailMessage(sender=from_email,
                                recipients=to,
                                subject=subject,
                                text_content=text_content,
                                html_content=html_content,
                                tags=['YU2 Account Confirm'])
            result = email.send()
            
            # Check if email wasn't sent.
            if not result['sent']:
                logger.error('Account Confirmation Email Not Sent! Result: ' + str(result['result']))
                raise
        except:
            logger.error('Unable to send confirmation email', exc_info=1)
            return False
        
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
    def new(email, valid_credentials, account_status, success, ip_address, metadata):
        """
        Logs an authentication event.
        """
        # Build authentication log.
        authlog = AuthenticationLog(email=email,
                                    valid_credentials=valid_credentials,
                                    account_status=account_status,
                                    success=success,
                                    ip_address=ip_address,
                                    metadata=metadata)
        
        # Shave and return.
        authlog.save()
        return authlog