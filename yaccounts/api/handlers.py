import datetime
import logging
from django.conf import settings
from django.contrib.auth import get_user_model, authenticate
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http.response import HttpResponse
from yapi.models import ApiKey
from yapi.authentication import SessionAuthentication, ApiKeyAuthentication
from yapi.resource import Resource
from yapi.response import HTTPStatus, Response
from yapi.utils import generate_key

from serializers import UserSerializer, UserPhotoSerializer, ApiKeySerializer
from yaccounts.exceptions import InvalidParameter
from yaccounts.forms import UserForm, UserPhotoForm

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


class ApiKeysHandler(Resource):
    """
    API endpoint handler.
    """
    # HTTP methods allowed.
    allowed_methods = ['POST', 'GET']
    
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
            
            # Update account photo and return.
            return Response(request=request,
                            data=request.auth['user'].set_photo(form.cleaned_data['file']),
                            serializer=UserPhotoSerializer,
                            status=HTTPStatus.SUCCESS_201_CREATED)
            
        # Form didn't validate!
        else:
            return Response(request=request,
                            data={ 'message': 'Invalid parameters', 'parameters': form.errors },
                            serializer=None,
                            status=HTTPStatus.CLIENT_ERROR_400_BAD_REQUEST)


class AuthenticationHandler(Resource):
    """
    API endpoint halder.
    """
    # HTTP methods allowed.
    allowed_methods = ['POST']
    
    def post(self, request):
        """
        Process POST request.
        """
        # Check if this feature is enabled.
        try:
            settings.YACCOUNTS['signup_available'].index('API')
        except:
            return HttpResponse(status=HTTPStatus.CLIENT_ERROR_404_NOT_FOUND)
        
        # Mandatory params.
        try:
            email = request.data['email']
            password = request.data['password']
            description = request.data['description']
        except KeyError:
            return Response(request=request,
                            data={ 'message': 'Missing parameters' },
                            serializer=None,
                            status=HTTPStatus.CLIENT_ERROR_400_BAD_REQUEST)
            
        # Validate credentials.
        user = authenticate(email=email, password=password)
        if user and user.is_active:
            
            # Check if there are any active API keys for given description.
            api_keys = ApiKey.objects.filter(user=user, active=True, description=description)
            
            # If there are, return the first.
            if api_keys:
                instance = api_keys[0]
                
            # If not, create one.
            else:
                instance = ApiKey(user=user,
                                  key=generate_key(email),
                                  description=description,
                                  active=True)
                instance.save()
            
            # Return.
            return Response(request=request,
                                data=instance,
                                serializer=ApiKeySerializer,
                                status=HTTPStatus.SUCCESS_200_OK)
            
        # Failed auhtentication.
        else:
            return HttpResponse(status=HTTPStatus.CLIENT_ERROR_401_UNAUTHORIZED)


class AccountRegisterHandler(Resource):
    """
    API endpoint handler.
    """
    # HTTP methods allowed.
    allowed_methods = ['POST', 'PUT']
    
    def post(self, request):
        """
        Process POST request.
        """
        # Check if this feature is enabled.
        try:
            settings.YACCOUNTS['signup_available'].index('API')
        except:
            return HttpResponse(status=HTTPStatus.CLIENT_ERROR_404_NOT_FOUND)
        
        # Mandatory params.
        try:
            name = request.data['name']
            email = request.data['email']
            password = request.data['password']
        except KeyError:
            return Response(request=request,
                            data={ 'message': 'Missing parameters' },
                            serializer=None,
                            status=HTTPStatus.CLIENT_ERROR_400_BAD_REQUEST)
        
        # Proceed with creating account.
        else:
            
            # If all parameters check, then a new account is created.
            try:
                new_user = get_user_model().new(name=name,
                                                email=email,
                                                password=password,
                                                credentials_type='api',
                                                email_activation_key=False)
                return Response(request=request,
                                data={ 'activation_key': new_user.activationkey.key },
                                serializer=None,
                                status=HTTPStatus.SUCCESS_201_CREATED)
            
            # Invalid parameters.
            except InvalidParameter as e:
                return Response(request=request,
                            data={ 'message': 'Invalid parameters', 'parameters': e.message },
                            serializer=None,
                            status=HTTPStatus.CLIENT_ERROR_400_BAD_REQUEST)
            
            # Unknown error.
            except:
                logger.error('Error creating account! Name: ' + str(name) + ', Email: ' + str(email), exc_info=1)
                return Response(request=request,
                            data={ 'message': 'Error creating account, please contact support.' },
                            serializer=None,
                            status=HTTPStatus.SERVER_ERROR_501_NOT_IMPLEMENTED)
    
    def put(self, request):
        """
        Process PUT request.
        """
        #
        # Should receive an activation key that, if valid, activates account.
        #
        
        # Check if this feature is enabled.
        try:
            settings.YACCOUNTS['signup_available'].index('API')
        except:
            return HttpResponse(status=HTTPStatus.CLIENT_ERROR_404_NOT_FOUND)
        
        # Mandatory params.
        try:
            email = request.data['email']
            activation_key = request.data['activation_key']
        except KeyError:
            return Response(request=request,
                            data={ 'message': 'Missing parameters' },
                            serializer=None,
                            status=HTTPStatus.CLIENT_ERROR_400_BAD_REQUEST)
            
        # Check if there is a user account waiting for activation (i.e. is disabled) with given email.
        try:
            user = get_user_model().objects.get(email=email, is_active=False)
        except ObjectDoesNotExist:
            return Response(request=request,
                            data={ 'message': 'Invalid user' },
                            serializer=None,
                            status=HTTPStatus.CLIENT_ERROR_400_BAD_REQUEST)
        
        # Check if user's activation key matches and hasn't been used. 
        if user.activationkey.key == activation_key and not user.activationkey.activated_at:
            
            # Mark activation key as used, by timestamping activation date.
            user.activationkey.activated_at = datetime.datetime.now()
            user.activationkey.save()
            
            # Activate account.
            user.is_active = True
            user.save()
            
            # Return great success!
            return HttpResponse(status=HTTPStatus.SUCCESS_200_OK)
        
        # Invalid activation key.
        else:
            return Response(request=request,
                            data={ 'message': 'Invalid activation key' },
                            serializer=None,
                            status=HTTPStatus.CLIENT_ERROR_400_BAD_REQUEST)