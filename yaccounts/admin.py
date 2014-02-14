from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.models import Group
from django.utils.translation import ugettext as _

from models import User, UserPhoto, ActivationKey, AuthenticationLog, ResetRequest, EmailUpdate, TwitterProfile, FacebookProfile


class UserCreationForm(forms.ModelForm):
    """
    A form for creating new users. Includes all the required fields, plus a repeated password.
    """
    password1 = forms.CharField(label=_("Password"), widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Password confirmation"), widget=forms.PasswordInput)

    class Meta:
        model = User

    def clean_password2(self):
        """
        Check that the two password entries match.
        """
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("Passwords don't match"))
        return password2

    def save(self, commit=True):
        """
        Save the provided password in hashed format.
        """
        user = super(UserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """
    A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    password hash display field.
    """
    password = ReadOnlyPasswordHashField(label=_("Password"),
        help_text= (_("Raw passwords are not stored, so there is no way to see "
                    "this user's password, but you can change the password "
                    "using <a href=\"password/\">this form</a>.")))

    class Meta:
        model = User

    def clean_password(self):
        """
        Regardless of what the user provides, return the initial value.
        This is done here, rather than on the field, because the
        field does not have access to the initial value
        """
        return self.initial['password']


class UserAdmin(UserAdmin):
    """
    Django admin for custom User model.
    """
    # The forms to add and change user instances.
    form = UserChangeForm
    add_form = UserCreationForm

    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.
    list_display = ('email', 'name', 'is_active', 'is_staff', 'is_superuser', 'created_at', 'created_via', 'last_login')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'created_via')
    fieldsets = (
        (None, { 'fields': ('name', 'email', 'password') }),
        #('Permissions', { 'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions') }), # We're not using Django authorization, yet.
        ('Permissions', { 'fields': ('is_active', 'is_staff', 'is_superuser') }),
        ('Important dates', { 'fields': ('last_login', 'created_at', 'created_via') })
    )
    add_fieldsets = (
        (None, { 'classes': ('wide',), 'fields': ('name', 'email', 'password1', 'password2') }),
    )
    search_fields = ('email',)
    ordering = ('email',)
    filter_horizontal = ('user_permissions',)
    readonly_fields = ('last_login', 'created_at', 'created_via')

# Register the custom User admin.
admin.site.register(User, UserAdmin)


class UserPhotoAdmin(admin.ModelAdmin):
    list_display = ('user', 'file')
admin.site.register(UserPhoto, UserPhotoAdmin)


class ActivationKeyAdmin(admin.ModelAdmin):
    list_display = ('user', 'key', 'created_at', 'activated_at')
    search_fields = ('user__email', 'key')
admin.site.register(ActivationKey, ActivationKeyAdmin)


class AuthenticationLogAdmin(admin.ModelAdmin):
    list_display = ('date', 'email', 'valid_credentials', 'credentials_type', 'account_status', 'ip_address', 'metadata', 'success')
    search_fields = ('email', 'ip_address')
    list_filter = ('valid_credentials', 'credentials_type', 'success', 'account_status')
admin.site.register(AuthenticationLog, AuthenticationLogAdmin)


class ResetRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'key', 'created_at', 'reset_at')
    search_fields = ('user__email', 'key')
admin.site.register(ResetRequest, ResetRequestAdmin)


class EmailUpdateAdmin(admin.ModelAdmin):
    list_display = ('user', 'old_email', 'new_email', 'key', 'created_at', 'updated_at')
    search_fields = ('user__email', 'old_email', 'new_email', 'key')
admin.site.register(EmailUpdate, EmailUpdateAdmin)


class TwitterProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'twitter_user_id', 'screen_name', 'created_at', 'last_used')
    search_fields = ('user__email', 'twitter_user_id', 'screen_name', 'access_token', 'access_token_secret')
admin.site.register(TwitterProfile, TwitterProfileAdmin)


class FacebookProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'facebook_user_id', 'name', 'created_at', 'last_used')
    search_fields = ('user__email', 'facebook_user_id', 'name', 'access_token')
admin.site.register(FacebookProfile, FacebookProfileAdmin)


# Unregister the Group model from admin (we're not using it, yet)
admin.site.unregister(Group)