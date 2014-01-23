import base64
import json
import logging

# Instantiate logger.
logger = logging.getLogger(__name__)


def process_confirmation_token(token):
    """
    Process confirmation token and, if valid, extract respective info.
    """
    try:
        # A valid token is a base64 encoded string.
        confirm_data = json.loads(base64.b64decode(token))
        
        # Containing the account's email, confirmation scenario and respective key.
        try:
            email = confirm_data['email']
            operation = confirm_data['operation']
            key = confirm_data['key']
            
            # If this place is reached, then the token is valid. Return respective info.
            return {
                'email': email,
                'operation': operation,
                'key': key
            }
            
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