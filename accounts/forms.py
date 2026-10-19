import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Profile


NAME_PATTERN = re.compile(r"^[^\W\d_]+([ '\-][^\W\d_]+)*$")  # letters (incl. ä, ë, ç), space, - and '
# Street name (starts with a letter) + house number, e.g. "Bayernallee 11", "Erste Str. 9a", "Am Markt 3-5"
STREET_PATTERN = re.compile(r"^[^\W\d_][\w .'\-]*?\s+\d{1,4}\s?[a-zA-Z]?(\s?[-/]\s?\d{1,4}\s?[a-zA-Z]?)?$")
POSTAL_CODE_PATTERN = re.compile(r"^\d{5}$")  # German postal code: exactly 5 digits
# City: letters, spaces, - . ( ) e.g. "Aachen", "Frankfurt am Main", "Halle (Saale)"
CITY_PATTERN = re.compile(r"^[^\W\d_][^\W\d_ .\-()]*([ .\-]+\(?[^\W\d_]+\)?)*\.?$")


def validate_name(value):
    value = value.strip()
    if not NAME_PATTERN.match(value):
        raise forms.ValidationError("Please use letters only (spaces, - and ' are allowed).")
    return value


def validate_street(value):
    value = " ".join(value.split())
    if not STREET_PATTERN.match(value):
        raise forms.ValidationError("Please enter the street name and house number, e.g. Bayernallee 11.")
    return value


def validate_postal_code(value):
    value = value.strip()
    if not POSTAL_CODE_PATTERN.match(value) or value == "00000":
        raise forms.ValidationError("Please enter a valid 5-digit postal code, e.g. 52066.")
    return value


def validate_city(value):
    value = " ".join(value.split())
    if len(value) < 2 or not CITY_PATTERN.match(value):
        raise forms.ValidationError("Please enter a valid city name (letters only), e.g. Aachen.")
    return value


class AddressFieldsMixin:
    """Street, postal code and city are checked separately."""

    def clean_street(self):
        return validate_street(self.cleaned_data["street"])

    def clean_postal_code(self):
        return validate_postal_code(self.cleaned_data["postal_code"])

    def clean_city(self):
        return validate_city(self.cleaned_data["city"])


class NameFieldsMixin:
    """First and last name: letters only, trimmed."""

    def clean_first_name(self):
        return validate_name(self.cleaned_data["first_name"])

    def clean_last_name(self):
        return validate_name(self.cleaned_data["last_name"])


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


class RegisterForm(BootstrapFormMixin, NameFieldsMixin, UniqueEmailMixin, AddressFieldsMixin, UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    street = forms.CharField(label="Street and house number", max_length=200)
    postal_code = forms.CharField(label="Postal code", max_length=5)
    city = forms.CharField(max_length=100)

    field_order = ["username", "first_name", "last_name", "email",
                   "street", "postal_code", "city", "password1", "password2"]

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile = user.profile
            profile.street = self.cleaned_data["street"]
            profile.postal_code = self.cleaned_data["postal_code"]
            profile.city = self.cleaned_data["city"]
            profile.save()
        return user


class UserUpdateForm(BootstrapFormMixin, NameFieldsMixin, UniqueEmailMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("first_name", "last_name", "email"):
            self.fields[name].required = True


class AddressForm(BootstrapFormMixin, AddressFieldsMixin, forms.ModelForm):
    """Street, postal code and city on the profile page (all required)."""

    class Meta:
        model = Profile
        fields = ["street", "postal_code", "city"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    pass


class StyledPasswordChangeForm(BootstrapFormMixin, PasswordChangeForm):
    pass
