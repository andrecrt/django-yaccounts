import Image
import logging
import os
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http.response import HttpResponse
from yapi.models import ApiKey
from yapi.authentication import SessionAuthentication, ApiKeyAuthentication
from yapi.resource import Resource
from yapi.response import HTTPStatus, Response
from yapi.utils import generate_key

from serializers import UserSerializer, UserPhotoSerializer, ApiKeySerializer
from yaccounts.forms import UserForm, UserPhotoForm
from yaccounts.models import UserPhoto

# Instantiate logger.
logger = logging.getLogger(__name__)


class AccountHandler(Resource):
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
        
        
class AccountPhotoHandler(Resource):
    """
    API endpoint handler.
    """
    # HTTP methods allowed.
    allowed_methods = ['POST', 'GET']
    
    # Authentication & Authorization.
    authentication = [SessionAuthentication, ApiKeyAuthentication]
    
    def get(self, request):
        """
        Process GET request.
        """
        # If user has photo.
        if hasattr(request.auth['user'], 'userphoto'):
            return Response(request=request,
                            data=request.auth['user'].userphoto,
                            serializer=UserPhotoSerializer,
                            status=HTTPStatus.SUCCESS_200_OK)
         
        # No photozzz!
        else:
            return HttpResponse(status=HTTPStatus.CLIENT_ERROR_404_NOT_FOUND)

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


class ApiKeysHandler(Resource):
    """
    API endpoint handler.
    """
    # HTTP methods allowed.
    allowed_methods = ['POST', 'GET', 'PUT']
    
    # Authentication & Authorization.
    authentication = [SessionAuthentication, ApiKeyAuthentication]
    
    def post(self, request):
        """
        Process POST request.
        """
        # Validate parameters.
        try:
            description = request.data['description']
        except KeyError:
            return Response(request=request,
                            data={ 'message': 'Missing parameter: description' },
                            serializer=None,
                            status=HTTPStatus.CLIENT_ERROR_400_BAD_REQUEST)
            
        # Create API key.
        api_key = ApiKey(user=request.auth['user'],
                        key=generate_key(request.auth['user'].email),
                        description=description,
                        active=True)
        api_key.save()
        
        # Return.
        return Response(request=request,
                        data=api_key,
                        serializer=ApiKeySerializer,
                        status=HTTPStatus.SUCCESS_201_CREATED)
        
    def get(self, request):
        """
        Process GET request.
        """
        #
        # Lets start with all.
        #
        results = ApiKey.objects.filter(user=request.auth['user']).order_by('created_at')
        
        #
        # Filters
        #
        filters = {}
        
        # Search description.
        try:
            description = request.GET['description']
            if description != '':
                results = results.filter(Q(description__icontains=description))
                filters['description'] = description
        except KeyError:
            pass
        
        # Status.
        try:
            active = request.GET['active']
            if active != '':
                # Validate parameter.
                if active.lower() != 'true' and active.lower() != 'false':
                    return Response(request=request,
                            data={ 'message': 'Invalid parameter value', 'param': 'active' },
                            serializer=None,
                            status=HTTPStatus.CLIENT_ERROR_400_BAD_REQUEST)
                # Business as usual...
                else:
                    is_active = active.lower() == 'true'
                    results = results.filter(active=is_active)
                    filters['active'] = is_active
        except KeyError:
            pass
        
        #
        # Return.
        #
        return Response(request=request,
                        data=results,
                        filters=filters,
                        serializer=ApiKeySerializer,
                        pagination=False,
                        status=HTTPStatus.SUCCESS_200_OK)


class ApiKeyIdHandler(Resource):
    """
    API endpoint handler.
    """
    # HTTP methods allowed.
    allowed_methods = ['GET', 'PUT', 'DELETE']
    
    # Authentication & Authorization.
    authentication = [SessionAuthentication, ApiKeyAuthentication]
    
    def get(self, request, pk):
        """
        Process GET request.
        """
        # Check if API key with given ID exists for given user.
        try:
            api_key = ApiKey.objects.get(user=request.auth['user'], id=pk)
        except ObjectDoesNotExist:
            return HttpResponse(status=HTTPStatus.CLIENT_ERROR_404_NOT_FOUND)
        
        # Return.
        return Response(request=request,
                        data=api_key,
                        serializer=ApiKeySerializer,
                        status=HTTPStatus.SUCCESS_200_OK)
        
    def put(self, request, pk):
        """
        Process PUT request.
        """
        # Check if API key with given ID exists for given user.
        try:
            api_key = ApiKey.objects.get(user=request.auth['user'], id=pk)
        except ObjectDoesNotExist:
            return HttpResponse(status=HTTPStatus.CLIENT_ERROR_404_NOT_FOUND)
        
        # Optional params.
        try:
            description = request.data['description']
        except KeyError:
            description = None
        try:
            active = request.data['active']
            # Validate param.
            if active == '' or (active != True and active != False):
                return Response(request=request,
                            data={ 'message': 'Invalid parameter value', 'param': 'active' },
                            serializer=None,
                            status=HTTPStatus.CLIENT_ERROR_400_BAD_REQUEST)
        except:
            active = None
            
        # Update.
        if description:
            api_key.description = description
        if active == True or active == False:
            api_key.active = active
        api_key.save()
        
        # Return.
        return HttpResponse(status=HTTPStatus.SUCCESS_200_OK)
        
    def delete(self, request, pk):
        """
        Process DELETE request.
        """
        # Check if API key with given ID exists for given user.
        try:
            api_key = ApiKey.objects.get(user=request.auth['user'], id=pk)
        except ObjectDoesNotExist:
            return HttpResponse(status=HTTPStatus.CLIENT_ERROR_404_NOT_FOUND)
        
        # Delete API key.
        api_key.delete()
        
        # Return.
        return HttpResponse(status=HTTPStatus.SUCCESS_204_NO_CONTENT)