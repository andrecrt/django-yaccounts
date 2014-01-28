import base64
import json
import logging
import types

# Instantiate logger.
logger = logging.getLogger(__name__)


class ConfirmationToken:
    """
    Response status codes.
    """
    
    # Available operations.
    ACCOUNT_ACTIVATION = 'activation'
    ACCOUNT_PASSWORD_RESET = 'password_reset'
    ACCOUNT_EMAIL_UPDATE = 'email_update'
    
    @staticmethod
    def generate(email, operation, key, more=None):
            """
            Returns a Base64 encoded string containing the confirmation data.
            """
            # Core token info.
            token = {
                'email': email,
                'operation': operation,
                'key': key
            }
            
            # Additional information.
            if more:
                if not isinstance(more, types.DictType):
                    raise TypeError("Expecting a dict")
                token.update(more)
                
            # Return.
            return base64.b64encode(json.dumps(token))
        
    @staticmethod
    def process(token):
        """
        Process confirmation token and, if valid, extract respective info.
        """
        try:
            # A valid token is a base64 encoded string.
            confirm_data = json.loads(base64.b64decode(token))
            
            # Containing the account's email, confirmation scenario and respective key.
            try:
                confirm_data['email']
                confirm_data['operation']
                confirm_data['key']
                
                # If this place is reached, then the token is valid. Return respective info.
                return confirm_data
                
            except KeyError:
                logger.info('Invalid account confirmation DATA! Data: ' + json.dumps(confirm_data))
                return None
        
        # Unable to b64 decode.
        except TypeError:
            logger.info('Invalid BASE64 account confirmation token! Token: ' + token)
            return None
        
        # Error decoding JSON
        except ValueError:
            logger.info('Invalid JSON account confirmation token! Token: ' + token)
            return None