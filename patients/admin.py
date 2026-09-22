from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import Patient

User = get_user_model()

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'date_of_birth',
        'blood_group',
        'created_at',
    )

    search_fields = (
        'user__username',
        'user__first_name',
        'user__last_name',
    )

def formfield_for_foreignkey(self, db_field, request, **kwargs):
    if db_field.name == "user":
        kwargs["queryset"] = User.objects.filter(role="PATIENT")

    return super().formfield_for_foreignkey(db_field, request, **kwargs)