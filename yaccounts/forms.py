from django import forms
from django.utils.translation import ugettext as _


class UserForm(forms.Form):
    """
    Form for updating User.
    """
    name = forms.CharField(max_length=100)
    password_old = forms.CharField(max_length=100, required=False)
    password_new = forms.CharField(max_length=100, required=False)
    password_confirm = forms.CharField(max_length=100, required=False)
    
    def __init__(self,*args,**kwargs):
        """
        Constructor.
        """
        self.user = kwargs.pop('user')
        super(UserForm,self).__init__(*args, **kwargs)
    
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