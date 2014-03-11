import logging
from django.conf import settings
from django.core.urlresolvers import reverse
from yapi.serializers import BaseSerializer

# Instantiate logger.
logger = logging.getLogger(__name__)


class UserSerializer(BaseSerializer):
    """
    Adds methods required for instance serialization.
    """
        
    def to_simple(self, obj, user=None):
        """
        Please refer to the interface documentation.
        """
        # Build response.
        simple = {
            'email': obj.email,
            'name': obj.name,
            'last_login': obj.last_login.strftime("%Y-%m-%d %H:%M:%S"),
            'photo': {
                'url': settings.HOST_URL + reverse(settings.YACCOUNTS['api_url_namespace'] + ':yaccounts:photo'),
                'image_url': obj.get_photo_url()
            },
            'api_keys': {
                'url': settings.HOST_URL + reverse(settings.YACCOUNTS['api_url_namespace'] + ':yaccounts:api_keys')
            }
        }
        
        # Twitter Profile.
        if hasattr(obj, 'twitterprofile'):
            simple['twitter_profile'] = {
                'twitter_user_id': obj.twitterprofile.twitter_user_id,
                'screen_name': obj.twitterprofile.screen_name,
                'profile_link': 'http://twitter.com/' + obj.twitterprofile.screen_name
            }
        
        # Facebook Profile.
        if hasattr(obj, 'facebookprofile'):
            simple['facebook_profile'] = {
                'facebook_user_id': obj.facebookprofile.facebook_user_id,
                'name': obj.facebookprofile.name,
                'profile_link': 'http://facebook.com/profile.php?id=' + obj.facebookprofile.facebook_user_id,
                'profile_image_url': obj.facebookprofile.get_photo_url()
            }
        
        # Return.
        return simple
    
    
class UserPhotoSerializer(BaseSerializer):
    """
    Adds methods required for instance serialization.
    """
    
    def to_simple(self, obj, user=None):
        """
        Please refer to the interface documentation.
        """
        simple = {
            'image_url': obj.file.url
        }        
        return simple
    
    
class ApiKeySerializer(BaseSerializer):
    """
    Adds methods required for instance serialization.
    """
    
    def to_simple(self, obj, user=None):
        """
        Please refer to the interface documentation.
        """
        # Build response.
        simple = {
            'id': obj.id,
            'url': settings.HOST_URL + reverse(settings.YACCOUNTS['api_url_namespace'] + ':yaccounts:api_key_id', args=[obj.id]),
            'key': obj.key,
            'description': obj.description,
            'created_at': obj.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'active': obj.active
        }
        if obj.last_used:
            simple['last_used'] = obj.last_used.strftime("%Y-%m-%d %H:%M:%S")
        
        # Return.
        return simple