from django.urls import path

from . import views


app_name = "admin_panel"


urlpatterns = [

    # ========================================================
    # DASHBOARD
    # ========================================================

    path(
        "",
        views.dashboard,
        name="dashboard"
    ),


    # ========================================================
    # USERS
    # ========================================================

    path(
        "users/",
        views.users,
        name="users"
    ),

    path(
        "users/add/",
        views.user_add,
        name="user_add"
    ),

    path(
        "users/<int:user_id>/",
        views.user_detail,
        name="user_detail"
    ),

    path(
        "users/<int:user_id>/edit/",
        views.user_edit,
        name="user_edit"
    ),

    path(
        "users/<int:user_id>/toggle-status/",
        views.user_toggle_status,
        name="user_toggle_status"
    ),


    # ========================================================
    # DOCTORS
    # ========================================================

    path(
        "doctors/",
        views.doctors,
        name="doctors"
    ),

    path(
        "doctors/<int:doctor_id>/toggle-availability/",
        views.doctor_toggle_availability,
        name="doctor_toggle_availability"
    ),
    path(
    "appointments/",
    views.appointments,
    name="appointments"
),
    path("appointments/", views.appointments, name="appointments"),
path("payments/", views.payments, name="payments"),

    path(
    "doctors/add/",
    views.doctor_add,
    name="doctor_add"
),


    # ========================================================
    # PATIENTS
    # ========================================================

    path(
        "patients/",
        views.patients,
        name="patients"
    ),

    path(
        "patients/add/",
        views.patient_add,
        name="patient_add"
    ),

    path(
        "patients/<int:patient_id>/",
        views.patient_detail,
        name="patient_detail"
    ),

    path(
        "patients/<int:patient_id>/edit/",
        views.patient_edit,
        name="patient_edit"
    ),

    path(
        "patients/<int:patient_id>/delete/",
        views.patient_delete,
        name="patient_delete"
    ),

]