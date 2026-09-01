from django import forms
from django.contrib.auth.models import User
from .models import Product, CourierProfile

class StudentSignUpForm(forms.ModelForm):
    # We add 'widget' to apply your specific CSS classes
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'case sensitive'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'input-field'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'input-field'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price', 'image', 'category', 'instock']


class CourierSignUpForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Create Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}))
    
    location_1 = forms.ChoiceField(choices=CourierProfile.HALL_CHOICES)
    location_2 = forms.ChoiceField(choices=CourierProfile.HALL_CHOICES, required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            # Create the profile automatically
            CourierProfile.objects.create(
                user=user,
                location_1=self.cleaned_data['location_1'],
                location_2=self.cleaned_data['location_2']
            )
        return user