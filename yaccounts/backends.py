import datetime
import logging
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from models import ActivationKey, TwitterProfile

# Instantiate logger.
logger = logging.getLogger(__name__)


class ActivationKeyAuthenticationBackend(object):
    """
    Authentication backend that validates user given activation key.
    """
    
    def authenticate(self, email, activation_key):
        """
        Mandatory method for Authentication Backends, validates provided set of credentials.
        """
        # Key cannot be empty string.
        if activation_key == '':
            return None
        
        # Check if there is an account with given email address.
        try:
            user = get_user_model().objects.get(email=email)
        except get_user_model().DoesNotExist:
            return None
        
        # Check if there is an unused activation for that account with given activation key.
        try:
            activation_key = ActivationKey.objects.get(user=user, key=activation_key, activated_at__isnull=True)
        except ObjectDoesNotExist:
            return None
        
        # Mark activation key as used, by timestamping activation date.
        activation_key.activated_at = datetime.datetime.now()
        activation_key.save()
        
        # Activate account.
        user.is_active = True
        user.save()
        
        # Return user.
        return user

    def get_user(self, user_id):
        """
        Mandatory method for Authentication Backends.
        """
        try:
            return get_user_model().objects.get(pk=user_id)
        except get_user_model().DoesNotExist:
            return None
        
        
class TwitterBackend:
    """
    Custom backend authentication to enable Twitter OAuth login.
    """

    def authenticate(self, twitter_userinfo, twitter_access_token):
        """
        Mandatory method for Authentication Backends, validates provided set of credentials.
        """
        try:
            # Validate credentials (i.e. check if this Twitter profile is already registered)
            twitter_profile = TwitterProfile.objects.get(twitter_user_id=twitter_userinfo.id)
        
            # Always update Twitter account information that comes with OAuth access token
            # (user might have revoked access to the application / changed screen name / etc)
            twitter_profile.update(twitter_userinfo, twitter_access_token)
            
            # If we're here, these credentials are valid (an account exists that is connected to this Twitter profile)
            return twitter_profile.user
        
        # Twitter profile not registered.
        except ObjectDoesNotExist:
            return None
            
    def get_user(self, user_id):
        """
        Mandatory method for Authentication Backends.
        """
        try:
            return get_user_model().objects.get(pk=user_id)
        except get_user_model().DoesNotExist:
            return None