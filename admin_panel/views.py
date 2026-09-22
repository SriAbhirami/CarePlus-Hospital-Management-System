from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages

from accounts.models import User
from patients.models import Patient
from doctors.models import Doctor
from appointments.models import Appointment


@login_required
def dashboard(request):
    # Only ADMIN users can access the Admin Panel
    if request.user.role != "ADMIN":
        messages.error(request, "You do not have permission to access the Admin Panel.")
        return redirect("admin_panel:dashboard")

    total_users = User.objects.count()
    total_patients = Patient.objects.count()
    total_doctors = Doctor.objects.count()
    total_appointments = Appointment.objects.count()

    pending_appointments = Appointment.objects.filter(
        status="PENDING"
    ).count()

    completed_appointments = Appointment.objects.filter(
        status="COMPLETED"
    ).count()

    cancelled_appointments = Appointment.objects.filter(
        status="CANCELLED"
    ).count()

    recent_appointments = Appointment.objects.select_related(
        "patient",
        "doctor"
    ).order_by("-created_at")[:8]

    context = {
        "total_users": total_users,
        "total_patients": total_patients,
        "total_doctors": total_doctors,
        "total_appointments": total_appointments,
        "pending_appointments": pending_appointments,
        "completed_appointments": completed_appointments,
        "cancelled_appointments": cancelled_appointments,
        "recent_appointments": recent_appointments,
    }

    return render(request, "admin_panel/dashboard.html", context)