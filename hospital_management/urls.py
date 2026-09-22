from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static


# ============================================================
# ACCOUNTS
# ============================================================

from accounts.views import (
    home_view,
    register_view,
    login_view,
    logout_view,
    about,
)


# ============================================================
# PATIENT
# ============================================================

from patients.views import (
    patient_dashboard,
    patient_bills,
    patient_prescriptions,
    patient_prescription_detail,
    patient_download_prescription_pdf,
    specialization_detail,
)


# ============================================================
# DOCTOR
# ============================================================

from doctors.views import (
    doctor_dashboard,
    doctor_appointments,
    create_prescription,
    doctor_prescriptions,
    doctor_prescription_detail,
    download_prescription_pdf,
    doctors_directory,
)


# ============================================================
# APPOINTMENTS / PAYMENTS
# ============================================================

from appointments.views import (
    book_appointment,
    pay_bills,
    process_payment,
    payment_success,
    payment_declined,
)


# ============================================================
# URL PATTERNS
# ============================================================

urlpatterns = [

    # --------------------------------------------------------
    # DJANGO ADMIN
    # --------------------------------------------------------

    path(
        'admin/',
        admin.site.urls
    ),


    # --------------------------------------------------------
    # PUBLIC / AUTHENTICATION
    # --------------------------------------------------------

    path(
        '',
        home_view,
        name='home'
    ),

    path(
        'login/',
        login_view,
        name='login'
    ),

    path(
        'register/',
        register_view,
        name='register'
    ),

    path(
        'logout/',
        logout_view,
        name='logout'
    ),

    path(
        'about/',
        about,
        name='about'
    ),


    # --------------------------------------------------------
    # PATIENT
    # --------------------------------------------------------

    path(
        'patient/dashboard/',
        patient_dashboard,
        name='patient_dashboard'
    ),

    path(
        'patient/book-appointment/',
        book_appointment,
        name='book_appointment'
    ),

    path(
        'patient/bills/',
        patient_bills,
        name='patient_bills'
    ),

    path(
        'patient/pay-bills/',
        pay_bills,
        name='pay_bills'
    ),

    path(
        'patient/process-payment/',
        process_payment,
        name='process_payment'
    ),

    path(
        'patient/payment-success/',
        payment_success,
        name='payment_success'
    ),

    path(
        'patient/payment-declined/',
        payment_declined,
        name='payment_declined'
    ),

    path(
        'patient/prescriptions/',
        patient_prescriptions,
        name='patient_prescriptions'
    ),

    path(
        'patient/prescriptions/<int:prescription_id>/',
        patient_prescription_detail,
        name='patient_prescription_detail'
    ),

    path(
        'patient/prescriptions/<int:prescription_id>/download/',
        patient_download_prescription_pdf,
        name='patient_download_prescription_pdf'
    ),

    path(
    'specializations/<str:specialization>/',
    specialization_detail,
    name='specialization_detail'
),


    # --------------------------------------------------------
    # DOCTOR
    # --------------------------------------------------------

    path(
        'doctor/dashboard/',
        doctor_dashboard,
        name='doctor_dashboard'
    ),

    path(
        'doctor/appointments/',
        doctor_appointments,
        name='doctor_appointments'
    ),

    path(
        'doctor/prescriptions/create/<int:appointment_id>/',
        create_prescription,
        name='create_prescription'
    ),

    path(
        'doctor/prescriptions/',
        doctor_prescriptions,
        name='doctor_prescriptions'
    ),

    path(
        'doctor/prescriptions/<int:prescription_id>/',
        doctor_prescription_detail,
        name='doctor_prescription_detail'
    ),

    path(
        'doctor/prescriptions/<int:prescription_id>/download/',
        download_prescription_pdf,
        name='download_prescription_pdf'
    ),

    path(
    'doctors/',
    doctors_directory,
    name='doctors_directory'
),


    # --------------------------------------------------------
    # ADMIN PANEL
    # --------------------------------------------------------

    path(
        'admin-panel/',
        include('admin_panel.urls')
    ),

]


# ============================================================
# MEDIA FILES
# ============================================================

urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)