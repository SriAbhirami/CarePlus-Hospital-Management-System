from django.contrib import admin

from .models import (
    Appointment,
    PaymentTransaction,
    Prescription,
    PrescriptionMedicine,
)


# ============================================================
# PRESCRIPTION MEDICINE INLINE
# ============================================================

class PrescriptionMedicineInline(admin.TabularInline):

    model = PrescriptionMedicine

    extra = 1


# ============================================================
# PRESCRIPTION ADMIN
# ============================================================

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'get_patient',
        'get_doctor',
        'appointment',
        'created_at',
    )

    search_fields = (
        'appointment__patient__user__username',
        'appointment__patient__user__first_name',
        'appointment__patient__user__last_name',
        'appointment__doctor__user__username',
        'appointment__doctor__user__first_name',
        'appointment__doctor__user__last_name',
    )

    list_filter = (
        'created_at',
    )

    inlines = [
        PrescriptionMedicineInline
    ]

    @admin.display(description='Patient')
    def get_patient(self, obj):

        return (
            obj.appointment.patient.user.get_full_name()
            or obj.appointment.patient.user.username
        )

    @admin.display(description='Doctor')
    def get_doctor(self, obj):

        return (
            obj.appointment.doctor.user.get_full_name()
            or obj.appointment.doctor.user.username
        )


# ============================================================
# PRESCRIPTION MEDICINE ADMIN
# ============================================================

@admin.register(PrescriptionMedicine)
class PrescriptionMedicineAdmin(admin.ModelAdmin):

    list_display = (
        'medicine_name',
        'dosage',
        'frequency',
        'duration',
        'prescription',
    )

    search_fields = (
        'medicine_name',
        'dosage',
        'frequency',
    )


# ============================================================
# APPOINTMENT ADMIN
# ============================================================

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'patient',
        'doctor',
        'appointment_date',
        'appointment_time',
        'status',
        'consultation_fee',
    )

    list_filter = (
        'status',
        'appointment_date',
    )

    search_fields = (
        'patient__user__username',
        'patient__user__first_name',
        'patient__user__last_name',
        'doctor__user__username',
        'doctor__user__first_name',
        'doctor__user__last_name',
    )


# ============================================================
# PAYMENT TRANSACTION ADMIN
# ============================================================

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):

    list_display = (
        'transaction_id',
        'patient',
        'doctor',
        'amount',
        'payment_method',
        'status',
        'appointment_date',
        'appointment_time',
        'created_at',
    )

    list_filter = (
        'status',
        'payment_method',
        'created_at',
    )

    search_fields = (
        'transaction_id',
        'patient__user__username',
        'patient__user__first_name',
        'patient__user__last_name',
        'doctor__user__username',
        'doctor__user__first_name',
        'doctor__user__last_name',
    )