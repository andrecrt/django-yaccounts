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
                'url': settings.HOST_URL + reverse(settings.YACCOUNTS['api_url_namespace'] + ':accounts:photo')
            }
        }
        
        # If user has photo.
        if hasattr(obj, 'userphoto'):
            simple['photo']['image_url'] = obj.userphoto.file.url
        
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