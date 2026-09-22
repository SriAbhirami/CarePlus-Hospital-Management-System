from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import Doctor
from .forms import DoctorAdminForm


User = get_user_model()


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):

    form = DoctorAdminForm

    list_display = (
        'user',
        'specialization',
        'qualification',
        'experience',
        'consultation_fee',
        'rating',
        'is_available',
    )

    list_filter = (
        'specialization',
        'is_available',
    )

    search_fields = (
        'user__username',
        'user__first_name',
        'user__last_name',
    )

    def save_model(self, request, obj, form, change):

        obj.user.role = 'DOCTOR'
        obj.user.save()

        super().save_model(
            request,
            obj,
            form,
            change
        )