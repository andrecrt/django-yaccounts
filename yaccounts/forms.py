import logging
from django import forms
from django.utils.translation import ugettext as _
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from models import EmailUpdate

# Instantiate logger.
logger = logging.getLogger(__name__)


class UserForm(forms.Form):
    """
    Form for updating User.
    """
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    password_old = forms.CharField(max_length=100, required=False)
    password_new = forms.CharField(max_length=100, required=False)
    password_confirm = forms.CharField(max_length=100, required=False)
    
    def __init__(self,*args,**kwargs):
        """
        Constructor.
        """
        self.user = kwargs.pop('user')
        super(UserForm,self).__init__(*args, **kwargs)
        
    def clean_email(self):
        """
        Add additional custom validation to field.
        """
        data = self.cleaned_data['email']
        
        # If email is different from the account's email address
        if self.user.email != data: 
            
            # 1) Check if there isn't a pending update request.
            if EmailUpdate.objects.filter(user=self.user, updated_at__isnull=True):
                raise forms.ValidationError('You already requested an email update. Verify or cancel.')
            
            # 2) If not, check if the new email isn't already registered.
            try:
                get_user_model().objects.get(email=data)
                raise forms.ValidationError('Email already registered.') 
            
            # If this place is reached, then email is different and not already registered with another account.
            except ObjectDoesNotExist:
                
                # Send email update confirmation to new email.
                try:
                    EmailUpdate.new(user=self.user, email=data)
                except:
                    logger.error('Unable to send email update confirmation! User: ' + self.user.email + ', Email Update: ' + data, exc_info=1)
                    raise forms.ValidationError('Unable to send email update confirmation email.')
                
                # Return.
                return data
    
    def clean(self):
        """
        Override default method to add additional validation.
        """
        # Superclass stuffz.
        cleaned_data = super(UserForm, self).clean()
        
        # New password provided.
        if cleaned_data.get('password_new'):
            
            # 1) Old password must check.
            if not cleaned_data.get('password_old'):
                self._errors['password_old'] = self.error_class([_('This field is required.')])
                del cleaned_data['password_new']
            elif not self.user.check_password(cleaned_data.get('password_old')):
                    self._errors['password_old'] = self.error_class([_('Invalid password.')])
                    del cleaned_data['password_new']
                    
            # 2) Double check new password with confirmation.
            elif not cleaned_data.get('password_confirm'):
                self._errors['password_confirm'] = self.error_class([_('This field is required.')])
                del cleaned_data['password_new']
            elif cleaned_data.get('password_confirm') != cleaned_data.get('password_new'):
                self._errors['password_confirm'] = self.error_class([_('Confirmation password doesn\'t match.')])
                del cleaned_data['password_new']
        
        # Return.
        return cleaned_data


class UserPhotoForm(forms.Form):
    """
    Form for User account photo.
    """
    file = forms.ImageField()