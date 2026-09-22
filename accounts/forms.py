from django import forms
from .models import User


class RegisterForm(forms.ModelForm):

    # Username
    username = forms.CharField(
        max_length=150
    )

    # Password
    password = forms.CharField(
        widget=forms.PasswordInput
    )

    # Confirm Password
    confirm_password = forms.CharField(
        widget=forms.PasswordInput
    )

    # Date of Birth
    date_of_birth = forms.DateField(
        widget=forms.DateInput(
            attrs={'type': 'date'}
        )
    )

    # Blood Group
    blood_group = forms.ChoiceField(
        choices=[
            ('', 'Select Blood Group'),
            ('A+', 'A+'),
            ('A-', 'A-'),
            ('B+', 'B+'),
            ('B-', 'B-'),
            ('AB+', 'AB+'),
            ('AB-', 'AB-'),
            ('O+', 'O+'),
            ('O-', 'O-'),
        ],
        required=False
    )

    # Allergies
    allergies = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'rows': 3,
                'placeholder': 'Mention any allergies'
            }
        ),
        required=False
    )

    # Address
    address = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'rows': 3,
                'placeholder': 'Enter your address'
            }
        ),
        required=False
    )

    class Meta:
        model = User

        fields = [
            'username',
            'password',
            'confirm_password',
            'first_name',
            'last_name',
            'email',
            'phone',
            'date_of_birth',
            'blood_group',
            'allergies',
            'address',
        ]

    def clean(self):

        cleaned_data = super().clean()

        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password:

            if password != confirm_password:

                raise forms.ValidationError(
                    "Passwords do not match."
                )

        return cleaned_data

    def save(self, commit=True):

        user = super().save(commit=False)

        user.set_password(
            self.cleaned_data['password']
        )

        user.role = 'PATIENT'

        if commit:
            user.save()

        return user


class LoginForm(forms.Form):

    username = forms.CharField(
        max_length=150
    )

    password = forms.CharField(
        widget=forms.PasswordInput
    )