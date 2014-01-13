import Image
import logging
import os

from serializers import UserSerializer, UserPhotoSerializer
from yaccounts.forms import UserForm, UserPhotoForm
from yaccounts.models import UserPhoto
from yapi.authentication import SessionAuthentication, ApiKeyAuthentication
from yapi.response import HTTPStatus, Response

# Instantiate logger.
logger = logging.getLogger(__name__)


class AccountHandler:
    """
    API endpoint handler.
    """
    # HTTP methods allowed.
    allowed_methods = ['GET', 'PUT']
    
    # Authentication & Authorization.
    authentication = [SessionAuthentication, ApiKeyAuthentication]
    
    def get(self, request):
        """
        Process GET request.
        """
        return Response(request=request,
                        data=request.auth['user'],
                        serializer=UserSerializer,
                        status=HTTPStatus.SUCCESS_200_OK)
        
    def put(self, request):
        """
        Process PUT request.
        """
        # Populate form with provided data.
        form = UserForm(request.data, user=request.auth['user'])
        
        # Provided data is valid.
        if form.is_valid():
            
            # Update account.
            request.auth['user'].update(name=form.cleaned_data['name'],
                                        password=form.cleaned_data['password_new'])
            
            # Return.
            return Response(request=request,
                            data=request.auth['user'],
                            serializer=UserSerializer,
                            status=HTTPStatus.SUCCESS_200_OK)
            
        # Form didn't validate!
        else:
            return Response(request=request,
                            data={ 'message': 'Invalid parameters', 'parameters': form.errors },
                            serializer=None,
                            status=HTTPStatus.CLIENT_ERROR_400_BAD_REQUEST)
        
        
class AccountPhotoHandler:
    """
    API endpoint handler.
    """
    # HTTP methods allowed.
    allowed_methods = ['POST']
    
    # Authentication & Authorization.
    authentication = [SessionAuthentication, ApiKeyAuthentication]
    
    def post(self, request):
        """
        Process POST request.
        """
        # Populate form with provided data.
        form = UserPhotoForm(request.POST, request.FILES)
        
        # Provided data is valid.
        if form.is_valid():
            
            # If user has photo.
            if hasattr(request.auth['user'], 'userphoto'):
                user_photo = request.auth['user'].userphoto
                # 1) Delete old file.
                os.remove(user_photo.file.path)
                # 2) Update with new one.
                user_photo.file = form.cleaned_data['file']
                
            # If not, create it.
            else:
                user_photo = UserPhoto(user=request.auth['user'],
                                       file=form.cleaned_data['file'])
                
            # Save.
            user_photo.save()
            
            # Resize image (user photos are fixed to 140x140)
            try:
                im = Image.open(user_photo.file.path)
                im = im.resize((140, 140), Image.ANTIALIAS)
                im.save(user_photo.file.path, format='JPEG')
            except IOError:
                logger.error('Error resizing user photo! User: ' + str(request.auth['user'].email))
                raise
            
            # Return.
            return Response(request=request,
                            data=user_photo,
                            serializer=UserPhotoSerializer,
                            status=HTTPStatus.SUCCESS_201_CREATED)
            
        # Form didn't validate!
        else:
            return Response(request=request,
                            data={ 'message': 'Invalid parameters', 'parameters': form.errors },
                            serializer=None,
                            status=HTTPStatus.CLIENT_ERROR_400_BAD_REQUEST)