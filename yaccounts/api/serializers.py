import logging

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
            'photo': None
        }
        
        # If user has photo.
        if hasattr(obj, 'userphoto'):
            simple['photo'] = {
                'url': obj.userphoto.file.url
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
            'url': obj.file.url
        }        
        return simple