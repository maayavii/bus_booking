from django import forms
from django.db import models
from django import forms
from myapp.models import BusRoute, Stop
from django.core.exceptions import ValidationError

from django.core.validators import RegexValidator
from django.contrib.auth import (
    authenticate,
    get_user_model

)

User = get_user_model()


class UserLoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self, *args, **kwargs):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise forms.ValidationError('This user does not exist')
            if not user.check_password(password):
                raise forms.ValidationError('Incorrect password')
            if not user.is_active:
                raise forms.ValidationError('This user is not active')
        return super(UserLoginForm, self).clean(*args, **kwargs)


class UserRegisterForm(forms.ModelForm):
    email = forms.EmailField(label='Email address')
    email2 = forms.EmailField(label='Confirm Email')
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'email2',
            'password'
        ]

    def clean(self, *args, **kwargs):
        email = self.cleaned_data.get('email')
        email2 = self.cleaned_data.get('email2')
        if email != email2:
            raise forms.ValidationError("Emails must match")
        email_qs = User.objects.filter(email=email)
        if email_qs.exists():
            raise forms.ValidationError(
                "This email has already been registered")
        return super(UserRegisterForm, self).clean(*args, **kwargs)
    
from .models import BusCompany, BusRoute, Bus, BusSchedule

class BusCompanyRegistrationForm(forms.ModelForm):
    """
    Form for bus companies to register their business
    """
    registration_number = forms.CharField(
        validators=[
            RegexValidator(
                regex=r'^[A-Z]{2}\d{6}$', 
                message='Registration number must be 2 letters followed by 6 digits'
            )
        ]
    )
    
    class Meta:
        model = BusCompany
        fields = [
            'company_name', 
            'registration_number', 
            'contact_email', 
            'contact_phone', 
            'address', 
            'website'
        ]
        exclude=['user','is_verified']
        widgets = {
            'website': forms.URLInput(attrs={'placeholder': 'Optional'}),
        }
        
        
class BusRouteForm(forms.ModelForm):
    """
    Form to add/edit bus routes with source and destination handling.
    """
    source_name = forms.CharField(
        max_length=255, 
        label="Source Stop",
        help_text="Enter or select the starting stop of the route"
    )
    
    destination_name = forms.CharField(
        max_length=255, 
        label="Destination Stop",
        help_text="Enter or select the ending stop of the route"
    )

    class Meta:
        model = BusRoute
        fields = [
            'route_name',
            'route_type',
            'total_distance',
            'base_fare_per_km'
        ]

    def __init__(self, *args, **kwargs):
        # Extract the user from kwargs if passed
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        """
        Validate source and destination stops.
        Create stops if they don't exist.
        """
        cleaned_data = super().clean()
        source_name = cleaned_data.get('source_name', '').strip()
        destination_name = cleaned_data.get('destination_name', '').strip()

        # Validate source and destination are provided
        if not source_name:
            raise ValidationError({
                'source_name': "Source stop is required."
            })

        if not destination_name:
            raise ValidationError({
                'destination_name': "Destination stop is required."
            })

        # Validate stops are different
        if source_name == destination_name:
            raise ValidationError({
                'destination_name': "Destination stop cannot be the same as the source stop."
            })

        # Validate company exists for the user
        if self.user:
            try:
                company = BusCompany.objects.get(user=self.user)
                cleaned_data['company'] = company
            except BusCompany.DoesNotExist:
                raise ValidationError("You must first register a bus company to add routes.")

        # Create or get source stop
        source_stop, _ = Stop.objects.get_or_create(
            name=source_name,
            defaults={'name': source_name}
        )
        cleaned_data['source'] = source_stop

        # Create or get destination stop
        destination_stop, _ = Stop.objects.get_or_create(
            name=destination_name,
            defaults={'name': destination_name}
        )
        cleaned_data['destination'] = destination_stop

        return cleaned_data

    def save(self, commit=True):
        """
        Override save method to ensure source and destination are set
        """
        # Retrieve the cleaned data
        source_stop = self.cleaned_data.get('source')
        destination_stop = self.cleaned_data.get('destination')
        company = self.cleaned_data.get('company')

        # Create the instance
        instance = super().save(commit=False)
        
        # Set source, destination, and company
        instance.source = source_stop
        instance.destination = destination_stop
        instance.company = company

        # Save if commit is True
        if commit:
            instance.save()
        
        return instance

class StopForm(forms.Form):
    """
    Form for individual stops within a route.
    """
    name = forms.CharField(max_length=255)
    order = forms.IntegerField(min_value=1)
class BusForm(forms.ModelForm):
    """
    Form to add buses to a route
    """
    def __init__(self, *args, **kwargs):
        routes = kwargs.pop('routes', None)
        super().__init__(*args, **kwargs)
        if routes:
            self.fields['route'].queryset = routes
    
    amenities = forms.MultipleChoiceField(
        choices=Bus.AMENITIES,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    class Meta:
        model = Bus
        fields = [
            'route', 
            'bus_number', 
            'bus_model', 
            'total_seats', 
            'available_seats', 
            'amenities',
            'departure_time', 
            'arrival_time', 
            'departure_date'
        ]
        widgets = {
            'departure_time': forms.TimeInput(attrs={'type': 'time'}),
            'arrival_time': forms.TimeInput(attrs={'type': 'time'}),
            'departure_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        total_seats = cleaned_data.get('total_seats')
        available_seats = cleaned_data.get('available_seats')
        
        if total_seats and available_seats and available_seats > total_seats:
            raise forms.ValidationError("Available seats cannot be more than total seats.")
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Convert amenities to JSON
        instance.amenities = self.cleaned_data.get('amenities', [])
        
        if commit:
            instance.save()
        return instance

class BusScheduleForm(forms.ModelForm):
    """
    Form to add bus schedules
    """
    class Meta:
        model = BusSchedule
        fields = ['day_of_week', 'departure_time']
        widgets = {
            'departure_time': forms.TimeInput(attrs={'type': 'time'}),
        }