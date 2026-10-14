from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
from django.contrib.auth.models import User


class BootstrapFormMixin:
    """Gives every field the Bootstrap 'form-control' look."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class UniqueEmailMixin:
    """Email identifies a customer, so two accounts may not share one (case-insensitive)."""

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        taken = User.objects.filter(email__iexact=email)
        if self.instance.pk:  # editing an existing user: ignore their own email
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class RegisterForm(BootstrapFormMixin, UniqueEmailMixin, UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            user.profile.address = self.cleaned_data["address"]
            user.profile.save()
        return user


class UserUpdateForm(BootstrapFormMixin, UniqueEmailMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True


class AddressForm(BootstrapFormMixin, forms.Form):
    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    pass


class StyledPasswordChangeForm(BootstrapFormMixin, PasswordChangeForm):
    pass
