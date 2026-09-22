from django import forms
from .models import Doctor


class DoctorAdminForm(forms.ModelForm):

    available_days = forms.MultipleChoiceField(
        choices=Doctor.DAYS_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Doctor
        fields = '__all__'

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # Convert the value stored in the database
        # from "MON,WED,FRI" into a list
        # that the checkboxes can understand.

        if self.instance and self.instance.available_days:

            self.initial['available_days'] = (
                self.instance.available_days.split(',')
            )

    def clean_available_days(self):

        days = self.cleaned_data['available_days']

        # Convert the selected checkboxes back into
        # "MON,WED,FRI" format for the database.

        return ','.join(days)