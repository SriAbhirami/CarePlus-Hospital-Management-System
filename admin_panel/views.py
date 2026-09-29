from decimal import Decimal, InvalidOperation
from functools import wraps

from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Count, Avg, Prefetch, prefetch_related_objects
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_time

from accounts.models import User
from patients.models import Patient
from doctors.models import Doctor
from appointments.models import Appointment


# ============================================================
# ADMIN ACCESS
# ============================================================

def admin_required(view_func):

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):

        if request.user.role != "ADMIN":
            messages.error(
                request,
                "You do not have permission to access the Admin Panel."
            )

            return redirect("home")

        return view_func(request, *args, **kwargs)

    return wrapper


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@admin_required
def dashboard(request):

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

    recent_appointments = (
        Appointment.objects
        .select_related(
            "patient",
            "patient__user",
            "doctor",
            "doctor__user"
        )
        .order_by("-created_at")[:8]
    )

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

    return render(
        request,
        "admin_panel/dashboard.html",
        context
    )


# ============================================================
# USERS - LIST
# ============================================================

@admin_required
def users(request):

    queryset = (
        User.objects
        .all()
        .order_by("-date_joined")
    )

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:

        queryset = queryset.filter(
            Q(username__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
        )

    role = request.GET.get(
        "role",
        ""
    ).strip()

    valid_roles = {
        choice[0]
        for choice in User.ROLE_CHOICES
    }

    if role in valid_roles:

        queryset = queryset.filter(
            role=role
        )

    status = request.GET.get(
        "status",
        ""
    ).strip()

    if status == "ACTIVE":

        queryset = queryset.filter(
            is_active=True
        )

    elif status == "INACTIVE":

        queryset = queryset.filter(
            is_active=False
        )

    total_users = User.objects.count()

    active_users = User.objects.filter(
        is_active=True
    ).count()

    inactive_users = User.objects.filter(
        is_active=False
    ).count()

    staff_users = User.objects.filter(
        role="STAFF"
    ).count()

    paginator = Paginator(
        queryset,
        10
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    context = {
        "users": page_obj,
        "page_obj": page_obj,

        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "staff_users": staff_users,

        "search": search,
        "selected_role": role,
        "selected_status": status,

        "role_choices": User.ROLE_CHOICES,
    }

    return render(
        request,
        "admin_panel/users.html",
        context
    )


# ============================================================
# USER - VIEW DETAILS
# ============================================================

@admin_required
def user_detail(request, user_id):

    user = get_object_or_404(
        User,
        id=user_id
    )

    patient_profile = None

    doctor_profile = None

    try:

        patient_profile = user.patient_profile

    except Exception:

        patient_profile = None

    try:

        doctor_profile = user.doctor_profile

    except Exception:

        doctor_profile = None

    context = {
        "user_obj": user,
        "patient_profile": patient_profile,
        "doctor_profile": doctor_profile,
    }

    return render(
        request,
        "admin_panel/user_detail.html",
        context
    )


# ============================================================
# USER - ADD
# ============================================================

@admin_required
def user_add(request):

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        first_name = request.POST.get(
            "first_name",
            ""
        ).strip()

        last_name = request.POST.get(
            "last_name",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        phone = request.POST.get(
            "phone",
            ""
        ).strip()

        role = request.POST.get(
            "role",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        confirm_password = request.POST.get(
            "confirm_password",
            ""
        )

        errors = []

        if not username:

            errors.append(
                "Username is required."
            )

        if User.objects.filter(
            username=username
        ).exists():

            errors.append(
                "This username is already in use."
            )

        if email and User.objects.filter(
            email=email
        ).exists():

            errors.append(
                "This email address is already in use."
            )

        valid_roles = {
            choice[0]
            for choice in User.ROLE_CHOICES
        }

        if role not in valid_roles:

            errors.append(
                "Please select a valid role."
            )

        if not password:

            errors.append(
                "Password is required."
            )

        if password != confirm_password:

            errors.append(
                "Passwords do not match."
            )

        doctor_data = {}

        if role == "DOCTOR":

            specialization = request.POST.get(
                "specialization",
                ""
            ).strip()

            qualification = request.POST.get(
                "qualification",
                ""
            ).strip()

            experience = request.POST.get(
                "experience",
                ""
            ).strip()

            consultation_fee = request.POST.get(
                "consultation_fee",
                ""
            ).strip()

            available_days = request.POST.getlist(
                "available_days"
            )

            available_time_start = request.POST.get(
                "available_time_start",
                ""
            ).strip()

            available_time_end = request.POST.get(
                "available_time_end",
                ""
            ).strip()

            rating = request.POST.get(
                "rating",
                "0"
            ).strip()

            is_available = (
                request.POST.get("is_available")
                == "on"
            )

            profile_pic = request.FILES.get(
                "profile_pic"
            )

            valid_specializations = {
                choice[0]
                for choice in Doctor.SPECIALIZATION_CHOICES
            }

            if specialization not in valid_specializations:

                errors.append(
                    "Please select a valid doctor specialization."
                )

            if not qualification:

                errors.append(
                    "Doctor qualification is required."
                )

            experience_value = None

            try:

                experience_value = int(
                    experience
                )

                if experience_value < 0:

                    errors.append(
                        "Experience cannot be negative."
                    )

            except (TypeError, ValueError):

                errors.append(
                    "Please enter a valid experience in years."
                )

            consultation_fee_value = None

            try:

                consultation_fee_value = Decimal(
                    consultation_fee
                )

                if consultation_fee_value < 0:

                    errors.append(
                        "Consultation fee cannot be negative."
                    )

            except (TypeError, InvalidOperation):

                errors.append(
                    "Please enter a valid consultation fee."
                )

            if not available_days:

                errors.append(
                    "Please select at least one available day."
                )

            valid_days = {
                choice[0]
                for choice in Doctor.DAYS_CHOICES
            }

            invalid_days = (
                set(available_days)
                - valid_days
            )

            if invalid_days:

                errors.append(
                    "Invalid availability day selected."
                )

            start_time_value = parse_time(
                available_time_start
            )

            end_time_value = parse_time(
                available_time_end
            )

            if not start_time_value:

                errors.append(
                    "Please enter a valid starting time."
                )

            if not end_time_value:

                errors.append(
                    "Please enter a valid ending time."
                )

            if (
                start_time_value
                and end_time_value
                and start_time_value >= end_time_value
            ):

                errors.append(
                    "Ending time must be later than starting time."
                )

            rating_value = None

            try:

                rating_value = Decimal(
                    rating or "0"
                )

                if (
                    rating_value < 0
                    or rating_value > 5
                ):

                    errors.append(
                        "Rating must be between 0 and 5."
                    )

            except (TypeError, InvalidOperation):

                errors.append(
                    "Please enter a valid rating."
                )

            doctor_data = {
                "specialization": specialization,
                "qualification": qualification,
                "experience": experience_value,
                "consultation_fee": consultation_fee_value,
                "available_days": ",".join(
                    available_days
                ),
                "available_time_start": start_time_value,
                "available_time_end": end_time_value,
                "profile_pic": profile_pic,
                "rating": rating_value,
                "is_available": is_available,
            }

        if not errors:

            try:

                with transaction.atomic():

                    user = User(
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        email=email,
                        phone=phone,
                        role=role,
                        is_active=True,
                    )

                    user.set_password(
                        password
                    )

                    user.save()

                    if role == "DOCTOR":

                        Doctor.objects.create(
                            user=user,
                            **doctor_data
                        )

                messages.success(
                    request,
                    f"User '{user.username}' was created successfully."
                )

                return redirect(
                    "admin_panel:user_detail",
                    user_id=user.id
                )

            except Exception:

                messages.error(
                    request,
                    "Unable to create the user. Please check the entered information."
                )

    context = {
        "role_choices": User.ROLE_CHOICES,

        "specialization_choices":
            Doctor.SPECIALIZATION_CHOICES,

        "days_choices":
            Doctor.DAYS_CHOICES,
    }

    return render(
        request,
        "admin_panel/user_form.html",
        context
    )


# ============================================================
# USER - EDIT
# ============================================================

@admin_required
def user_edit(request, user_id):

    user = get_object_or_404(
        User,
        id=user_id
    )

    doctor_profile = None

    try:

        doctor_profile = user.doctor_profile

    except Exception:

        doctor_profile = None

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        first_name = request.POST.get(
            "first_name",
            ""
        ).strip()

        last_name = request.POST.get(
            "last_name",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        phone = request.POST.get(
            "phone",
            ""
        ).strip()

        role = request.POST.get(
            "role",
            ""
        ).strip()

        errors = []

        if not username:

            errors.append(
                "Username is required."
            )

        if User.objects.filter(
            username=username
        ).exclude(
            id=user.id
        ).exists():

            errors.append(
                "This username is already in use."
            )

        if email and User.objects.filter(
            email=email
        ).exclude(
            id=user.id
        ).exists():

            errors.append(
                "This email address is already in use."
            )

        valid_roles = {
            choice[0]
            for choice in User.ROLE_CHOICES
        }

        if role not in valid_roles:

            errors.append(
                "Please select a valid role."
            )

        doctor_data = {}

        if role == "DOCTOR":

            specialization = request.POST.get(
                "specialization",
                ""
            ).strip()

            qualification = request.POST.get(
                "qualification",
                ""
            ).strip()

            experience = request.POST.get(
                "experience",
                ""
            ).strip()

            consultation_fee = request.POST.get(
                "consultation_fee",
                ""
            ).strip()

            available_days = request.POST.getlist(
                "available_days"
            )

            available_time_start = request.POST.get(
                "available_time_start",
                ""
            ).strip()

            available_time_end = request.POST.get(
                "available_time_end",
                ""
            ).strip()

            rating = request.POST.get(
                "rating",
                "0"
            ).strip()

            is_available = (
                request.POST.get("is_available")
                == "on"
            )

            profile_pic = request.FILES.get(
                "profile_pic"
            )

            valid_specializations = {
                choice[0]
                for choice in Doctor.SPECIALIZATION_CHOICES
            }

            if specialization not in valid_specializations:

                errors.append(
                    "Please select a valid doctor specialization."
                )

            if not qualification:

                errors.append(
                    "Doctor qualification is required."
                )

            experience_value = None

            try:

                experience_value = int(
                    experience
                )

                if experience_value < 0:

                    errors.append(
                        "Experience cannot be negative."
                    )

            except (TypeError, ValueError):

                errors.append(
                    "Please enter a valid experience in years."
                )

            consultation_fee_value = None

            try:

                consultation_fee_value = Decimal(
                    consultation_fee
                )

                if consultation_fee_value < 0:

                    errors.append(
                        "Consultation fee cannot be negative."
                    )

            except (TypeError, InvalidOperation):

                errors.append(
                    "Please enter a valid consultation fee."
                )

            if not available_days:

                errors.append(
                    "Please select at least one available day."
                )

            valid_days = {
                choice[0]
                for choice in Doctor.DAYS_CHOICES
            }

            if set(available_days) - valid_days:

                errors.append(
                    "Invalid availability day selected."
                )

            start_time_value = parse_time(
                available_time_start
            )

            end_time_value = parse_time(
                available_time_end
            )

            if not start_time_value:

                errors.append(
                    "Please enter a valid starting time."
                )

            if not end_time_value:

                errors.append(
                    "Please enter a valid ending time."
                )

            if (
                start_time_value
                and end_time_value
                and start_time_value >= end_time_value
            ):

                errors.append(
                    "Ending time must be later than starting time."
                )

            rating_value = None

            try:

                rating_value = Decimal(
                    rating or "0"
                )

                if (
                    rating_value < 0
                    or rating_value > 5
                ):

                    errors.append(
                        "Rating must be between 0 and 5."
                    )

            except (TypeError, InvalidOperation):

                errors.append(
                    "Please enter a valid rating."
                )

            doctor_data = {
                "specialization": specialization,
                "qualification": qualification,
                "experience": experience_value,
                "consultation_fee": consultation_fee_value,
                "available_days": ",".join(
                    available_days
                ),
                "available_time_start": start_time_value,
                "available_time_end": end_time_value,
                "rating": rating_value,
                "is_available": is_available,
            }

            if profile_pic:

                doctor_data["profile_pic"] = profile_pic

        if not errors:

            try:

                with transaction.atomic():

                    user.username = username

                    user.first_name = first_name

                    user.last_name = last_name

                    user.email = email

                    user.phone = phone

                    user.role = role

                    user.save()

                    if role == "DOCTOR":

                        if doctor_profile:

                            for field, value in doctor_data.items():

                                setattr(
                                    doctor_profile,
                                    field,
                                    value
                                )

                            doctor_profile.save()

                        else:

                            Doctor.objects.create(
                                user=user,
                                **doctor_data
                            )

                messages.success(
                    request,
                    f"User '{user.username}' was updated successfully."
                )

                return redirect(
                    "admin_panel:user_detail",
                    user_id=user.id
                )

            except Exception:

                messages.error(
                    request,
                    "Unable to update the user. Please check the entered information."
                )

    selected_days = []

    if (
        doctor_profile
        and doctor_profile.available_days
    ):

        selected_days = [
            day.strip()
            for day in doctor_profile.available_days.split(",")
            if day.strip()
        ]

    context = {
        "user_obj": user,

        "doctor_profile":
            doctor_profile,

        "role_choices":
            User.ROLE_CHOICES,

        "specialization_choices":
            Doctor.SPECIALIZATION_CHOICES,

        "days_choices":
            Doctor.DAYS_CHOICES,

        "selected_days":
            selected_days,

        "is_edit":
            True,
    }

    return render(
        request,
        "admin_panel/user_form.html",
        context
    )


# ============================================================
# USER - ACTIVATE / DEACTIVATE
# ============================================================

@admin_required
def user_toggle_status(request, user_id):

    user = get_object_or_404(
        User,
        id=user_id
    )

    if request.method != "POST":

        return redirect(
            "admin_panel:users"
        )

    if (
        user.id == request.user.id
        and user.is_active
    ):

        messages.error(
            request,
            "You cannot deactivate your own admin account."
        )

        return redirect(
            "admin_panel:users"
        )

    user.is_active = not user.is_active

    user.save(
        update_fields=["is_active"]
    )

    if user.is_active:

        messages.success(
            request,
            f"{user.username} has been activated."
        )

    else:

        messages.success(
            request,
            f"{user.username} has been deactivated."
        )

    return redirect(
        "admin_panel:users"
    )


# ============================================================
# DOCTORS - LIST
# ============================================================

@admin_required
def doctors(request):

    today = timezone.localdate()

    queryset = (
        Doctor.objects
        .select_related("user")
        .annotate(

            appointment_count=Count(
                "appointments",
                distinct=True
            ),

            completed_count=Count(
                "appointments",
                filter=Q(
                    appointments__status="COMPLETED"
                ),
                distinct=True
            ),

            pending_count=Count(
                "appointments",
                filter=Q(
                    appointments__status="PENDING"
                ),
                distinct=True
            ),

            confirmed_count=Count(
                "appointments",
                filter=Q(
                    appointments__status="CONFIRMED"
                ),
                distinct=True
            ),

            cancelled_count=Count(
                "appointments",
                filter=Q(
                    appointments__status="CANCELLED"
                ),
                distinct=True
            ),
        )
        .order_by(
            "-is_available",
            "user__first_name",
            "user__last_name"
        )
    )

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:

        queryset = queryset.filter(

            Q(
                user__username__icontains=search
            )

            |

            Q(
                user__first_name__icontains=search
            )

            |

            Q(
                user__last_name__icontains=search
            )

            |

            Q(
                qualification__icontains=search
            )
        )

    # --------------------------------------------------------
    # SPECIALIZATION FILTER
    # --------------------------------------------------------

    specialization = request.GET.get(
        "specialization",
        ""
    ).strip()

    valid_specializations = {
        choice[0]
        for choice in Doctor.SPECIALIZATION_CHOICES
    }

    if specialization in valid_specializations:

        queryset = queryset.filter(
            specialization=specialization
        )

    # --------------------------------------------------------
    # AVAILABILITY FILTER
    # --------------------------------------------------------

    availability = request.GET.get(
        "availability",
        ""
    ).strip()

    if availability == "AVAILABLE":

        queryset = queryset.filter(
            is_available=True
        )

    elif availability == "UNAVAILABLE":

        queryset = queryset.filter(
            is_available=False
        )

    # --------------------------------------------------------
    # SUMMARY STATISTICS
    # --------------------------------------------------------

    total_doctors = Doctor.objects.count()

    available_doctors = Doctor.objects.filter(
        is_available=True
    ).count()

    appointments_today = Appointment.objects.filter(
        appointment_date=today
    ).count()

    rating_average = Doctor.objects.filter(
        rating__gt=0
    ).aggregate(
        average=Avg("rating")
    )["average"]

    if rating_average is None:

        rating_average = Decimal("0.0")

    # --------------------------------------------------------
    # PAGINATION
    # --------------------------------------------------------

    paginator = Paginator(
        queryset,
        8
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    # --------------------------------------------------------
    # TODAY'S APPOINTMENTS
    # --------------------------------------------------------

    today_appointments_queryset = (
        Appointment.objects
        .filter(
            appointment_date=today
        )
        .select_related(
            "patient",
            "patient__user"
        )
        .order_by(
            "appointment_time"
        )
    )

    # --------------------------------------------------------
    # RECENT APPOINTMENTS
    # --------------------------------------------------------

    recent_appointments_queryset = (
        Appointment.objects
        .select_related(
            "patient",
            "patient__user"
        )
        .order_by(
            "-appointment_date",
            "-appointment_time"
        )
    )

    # --------------------------------------------------------
    # BULK PREFETCH
    # --------------------------------------------------------

    prefetch_related_objects(

        page_obj.object_list,

        Prefetch(
            "appointments",
            queryset=today_appointments_queryset,
            to_attr="today_appointments"
        ),

        Prefetch(
            "appointments",
            queryset=recent_appointments_queryset,
            to_attr="all_recent_appointments"
        ),
    )

    # --------------------------------------------------------
    # PREPARE TEMPLATE DATA
    # --------------------------------------------------------

    day_label_map = dict(
        Doctor.DAYS_CHOICES
    )

    for doctor in page_obj:

        doctor.available_day_labels = []

        available_day_values = [
            day.strip()
            for day in (
                doctor.available_days or ""
            ).split(",")
            if day.strip()
        ]

        for day in available_day_values:

            if day in day_label_map:

                doctor.available_day_labels.append(
                    day_label_map[day]
                )

        doctor.recent_appointments = (
            getattr(
                doctor,
                "all_recent_appointments",
                []
            )[:5]
        )

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context = {

        "doctors":
            page_obj,

        "page_obj":
            page_obj,

        "total_doctors":
            total_doctors,

        "available_doctors":
            available_doctors,

        "appointments_today":
            appointments_today,

        "rating_average":
            rating_average,

        "search":
            search,

        "selected_specialization":
            specialization,

        "selected_availability":
            availability,

        "specialization_choices":
            Doctor.SPECIALIZATION_CHOICES,
    }

    return render(
        request,
        "admin_panel/doctors.html",
        context
    )


# ============================================================
# DOCTOR - TOGGLE AVAILABILITY
# ============================================================

@admin_required
def doctor_toggle_availability(
    request,
    doctor_id
):

    doctor = get_object_or_404(
        Doctor,
        id=doctor_id
    )

    if request.method != "POST":

        return redirect(
            "admin_panel:doctors"
        )

    doctor.is_available = (
        not doctor.is_available
    )

    doctor.save(
        update_fields=["is_available"]
    )

    if doctor.is_available:

        messages.success(
            request,
            f"Dr. {doctor.user.get_full_name() or doctor.user.username} "
            "is now available for appointments."
        )

    else:

        messages.success(
            request,
            f"Dr. {doctor.user.get_full_name() or doctor.user.username} "
            "has been marked unavailable."
        )

    return redirect(
        "admin_panel:doctors"
    )

# ============================================================
# APPOINTMENTS - LIST
# ============================================================

@admin_required
def appointments(request):
    """
    Display and manage all hospital appointments.

    Supports:
    - Search by patient / doctor
    - Status filtering
    - Doctor filtering
    - Specialization filtering
    - Appointment date filtering
    - Pagination
    """

    today = timezone.localdate()

    # --------------------------------------------------------
    # BASE QUERYSET
    # --------------------------------------------------------

    queryset = (
        Appointment.objects
        .select_related(
            "patient",
            "patient__user",
            "doctor",
            "doctor__user",
        )
        .order_by(
            "appointment_date",
            "appointment_time",
        )
    )

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:

        queryset = queryset.filter(
            Q(
                patient__user__username__icontains=search
            )
            |
            Q(
                patient__user__first_name__icontains=search
            )
            |
            Q(
                patient__user__last_name__icontains=search
            )
            |
            Q(
                patient__user__email__icontains=search
            )
            |
            Q(
                patient__user__phone__icontains=search
            )
            |
            Q(
                doctor__user__username__icontains=search
            )
            |
            Q(
                doctor__user__first_name__icontains=search
            )
            |
            Q(
                doctor__user__last_name__icontains=search
            )
            |
            Q(
                reason__icontains=search
            )
        )

    # --------------------------------------------------------
    # STATUS FILTER
    # --------------------------------------------------------

    status = request.GET.get(
        "status",
        ""
    ).strip()

    valid_statuses = {
        choice[0]
        for choice in Appointment.STATUS_CHOICES
    }

    if status in valid_statuses:

        queryset = queryset.filter(
            status=status
        )

    # --------------------------------------------------------
    # SPECIALIZATION FILTER
    # --------------------------------------------------------

    specialization = request.GET.get(
        "specialization",
        ""
    ).strip()

    valid_specializations = {
        choice[0]
        for choice in Doctor.SPECIALIZATION_CHOICES
    }

    if specialization in valid_specializations:

        queryset = queryset.filter(
            doctor__specialization=specialization
        )

    # --------------------------------------------------------
    # DOCTOR FILTER
    # --------------------------------------------------------

    doctor_id = request.GET.get(
        "doctor",
        ""
    ).strip()

    if doctor_id.isdigit():

        queryset = queryset.filter(
            doctor_id=int(doctor_id)
        )

    # --------------------------------------------------------
    # DATE FILTER
    # --------------------------------------------------------

    appointment_date = request.GET.get(
        "date",
        ""
    ).strip()

    if appointment_date:

        queryset = queryset.filter(
            appointment_date=appointment_date
        )

    # --------------------------------------------------------
    # SUMMARY STATISTICS
    # --------------------------------------------------------

    total_appointments = Appointment.objects.count()

    today_appointments = Appointment.objects.filter(
        appointment_date=today
    ).count()

    pending_appointments = Appointment.objects.filter(
        status="PENDING"
    ).count()

    confirmed_appointments = Appointment.objects.filter(
        status="CONFIRMED"
    ).count()

    completed_appointments = Appointment.objects.filter(
        status="COMPLETED"
    ).count()

    cancelled_appointments = Appointment.objects.filter(
        status="CANCELLED"
    ).count()

    # --------------------------------------------------------
    # DOCTOR FILTER OPTIONS
    # --------------------------------------------------------

    doctors_list = (
        Doctor.objects
        .select_related("user")
        .order_by(
            "user__first_name",
            "user__last_name"
        )
    )

    # --------------------------------------------------------
    # PAGINATION
    # --------------------------------------------------------

    paginator = Paginator(
        queryset,
        10
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context = {

        # Appointment data
        "appointments":
            page_obj,

        "page_obj":
            page_obj,

        # Statistics
        "total_appointments":
            total_appointments,

        "today_appointments":
            today_appointments,

        "pending_appointments":
            pending_appointments,

        "confirmed_appointments":
            confirmed_appointments,

        "completed_appointments":
            completed_appointments,

        "cancelled_appointments":
            cancelled_appointments,

        # Filters
        "search":
            search,

        "selected_status":
            status,

        "selected_specialization":
            specialization,

        "selected_doctor":
            doctor_id,

        "selected_date":
            appointment_date,

        # Filter choices
        "status_choices":
            Appointment.STATUS_CHOICES,

        "specialization_choices":
            Doctor.SPECIALIZATION_CHOICES,

        "doctors_list":
            doctors_list,

    }

    return render(
        request,
        "admin_panel/appointments.html",
        context
    )

@admin_required
def payments(request):
    today = timezone.localdate()

    queryset = (
        PaymentTransaction.objects
        .select_related(
            "patient",
            "patient__user",
            "doctor",
            "doctor__user",
            "appointment",
        )
        .order_by("-created_at")
    )

    # ---------------------------------------------------------
    # SEARCH
    # ---------------------------------------------------------
    search = request.GET.get("search", "").strip()

    if search:
        queryset = queryset.filter(
            Q(transaction_id__icontains=search)
            | Q(patient__user__username__icontains=search)
            | Q(patient__user__first_name__icontains=search)
            | Q(patient__user__last_name__icontains=search)
            | Q(patient__user__email__icontains=search)
            | Q(patient__user__phone__icontains=search)
            | Q(doctor__user__username__icontains=search)
            | Q(doctor__user__first_name__icontains=search)
            | Q(doctor__user__last_name__icontains=search)
        )

    # ---------------------------------------------------------
    # PAYMENT STATUS FILTER
    # ---------------------------------------------------------
    payment_status = request.GET.get("status", "").strip()

    valid_statuses = {
        choice[0]
        for choice in PaymentTransaction.STATUS_CHOICES
    }

    if payment_status in valid_statuses:
        queryset = queryset.filter(status=payment_status)

    # ---------------------------------------------------------
    # PAYMENT METHOD FILTER
    # ---------------------------------------------------------
    payment_method = request.GET.get("method", "").strip()

    valid_methods = {
        choice[0]
        for choice in PaymentTransaction.PAYMENT_METHOD_CHOICES
    }

    if payment_method in valid_methods:
        queryset = queryset.filter(payment_method=payment_method)

    # ---------------------------------------------------------
    # DOCTOR FILTER
    # ---------------------------------------------------------
    doctor_id = request.GET.get("doctor", "").strip()

    if doctor_id.isdigit():
        queryset = queryset.filter(doctor_id=int(doctor_id))

    # ---------------------------------------------------------
    # DATE FILTER
    # ---------------------------------------------------------
    payment_date = request.GET.get("date", "").strip()

    if payment_date:
        queryset = queryset.filter(
            created_at__date=payment_date
        )

    # ---------------------------------------------------------
    # GLOBAL PAYMENT STATISTICS
    # ---------------------------------------------------------
    total_transactions = PaymentTransaction.objects.count()

    successful_payments = PaymentTransaction.objects.filter(
        status="SUCCESS"
    ).count()

    declined_payments = PaymentTransaction.objects.filter(
        status="DECLINED"
    ).count()

    total_revenue = (
        PaymentTransaction.objects
        .filter(status="SUCCESS")
        .aggregate(total=Sum("amount"))
        ["total"]
        or 0
    )

    today_transactions = PaymentTransaction.objects.filter(
        created_at__date=today
    ).count()

    today_revenue = (
        PaymentTransaction.objects
        .filter(
            status="SUCCESS",
            created_at__date=today,
        )
        .aggregate(total=Sum("amount"))
        ["total"]
        or 0
    )

    # ---------------------------------------------------------
    # DOCTOR LIST FOR FILTER
    # ---------------------------------------------------------
    doctors_list = (
        Doctor.objects
        .select_related("user")
        .order_by(
            "user__first_name",
            "user__last_name",
        )
    )

    # ---------------------------------------------------------
    # PAGINATION
    # ---------------------------------------------------------
    paginator = Paginator(queryset, 10)

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "payments": page_obj,
        "page_obj": page_obj,

        # Statistics
        "total_transactions": total_transactions,
        "successful_payments": successful_payments,
        "declined_payments": declined_payments,
        "total_revenue": total_revenue,
        "today_transactions": today_transactions,
        "today_revenue": today_revenue,

        # Filters
        "search": search,
        "selected_status": payment_status,
        "selected_method": payment_method,
        "selected_doctor": doctor_id,
        "selected_date": payment_date,

        # Choices
        "status_choices": PaymentTransaction.STATUS_CHOICES,
        "payment_method_choices": PaymentTransaction.PAYMENT_METHOD_CHOICES,

        # Doctors
        "doctors_list": doctors_list,
    }

    return render(
        request,
        "admin_panel/payments.html",
        context
    )

# ============================================================
# PATIENTS - LIST
# ============================================================

@admin_required
def patients(request):

    today = timezone.localdate()

    # --------------------------------------------------------
    # BASE PATIENT QUERY
    # --------------------------------------------------------

    queryset = (
        Patient.objects
        .select_related("user")
        .annotate(
            appointment_count=Count(
                "appointments",
                distinct=True
            ),
            completed_count=Count(
                "appointments",
                filter=Q(
                    appointments__status="COMPLETED"
                ),
                distinct=True
            ),
            pending_count=Count(
                "appointments",
                filter=Q(
                    appointments__status="PENDING"
                ),
                distinct=True
            ),
            confirmed_count=Count(
                "appointments",
                filter=Q(
                    appointments__status="CONFIRMED"
                ),
                distinct=True
            ),
            cancelled_count=Count(
                "appointments",
                filter=Q(
                    appointments__status="CANCELLED"
                ),
                distinct=True
            ),
        )
        .order_by(
            "user__first_name",
            "user__last_name"
        )
    )

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:

        queryset = queryset.filter(
            Q(
                user__username__icontains=search
            )
            |
            Q(
                user__first_name__icontains=search
            )
            |
            Q(
                user__last_name__icontains=search
            )
            |
            Q(
                user__email__icontains=search
            )
            |
            Q(
                user__phone__icontains=search
            )
        )

    # --------------------------------------------------------
    # BLOOD GROUP FILTER
    # --------------------------------------------------------

    blood_group = request.GET.get(
        "blood_group",
        ""
    ).strip()

    valid_blood_groups = {
        choice[0]
        for choice in Patient.BLOOD_GROUP_CHOICES
    }

    if blood_group in valid_blood_groups:

        queryset = queryset.filter(
            blood_group=blood_group
        )

    # --------------------------------------------------------
    # STATUS FILTER
    # --------------------------------------------------------

    status = request.GET.get(
        "status",
        ""
    ).strip()

    if status == "ACTIVE":

        queryset = queryset.filter(
            user__is_active=True
        )

    elif status == "INACTIVE":

        queryset = queryset.filter(
            user__is_active=False
        )

    # --------------------------------------------------------
    # SUMMARY STATISTICS
    # --------------------------------------------------------

    total_patients = Patient.objects.count()

    active_patients = Patient.objects.filter(
        user__is_active=True
    ).count()

    inactive_patients = Patient.objects.filter(
        user__is_active=False
    ).count()

    patients_with_appointments = (
        Patient.objects
        .filter(
            appointments__isnull=False
        )
        .distinct()
        .count()
    )

    # --------------------------------------------------------
    # NEW PATIENTS
    # --------------------------------------------------------

    first_day_of_month = today.replace(day=1)

    new_patients = Patient.objects.filter(
        created_at__date__gte=first_day_of_month
    ).count()

    # --------------------------------------------------------
    # PAGINATION
    # --------------------------------------------------------

    paginator = Paginator(
        queryset,
        10
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    # --------------------------------------------------------
    # RECENT / LAST APPOINTMENTS
    # --------------------------------------------------------

    appointment_queryset = (
        Appointment.objects
        .select_related(
            "doctor",
            "doctor__user"
        )
        .order_by(
            "-appointment_date",
            "-appointment_time"
        )
    )

    prefetch_related_objects(
        page_obj.object_list,
        Prefetch(
            "appointments",
            queryset=appointment_queryset,
            to_attr="all_appointments"
        )
    )

    # --------------------------------------------------------
    # PREPARE TEMPLATE DATA
    # --------------------------------------------------------

    for patient in page_obj:

        appointments = getattr(
            patient,
            "all_appointments",
            []
        )

        patient.recent_appointments = appointments[:5]

        patient.last_visit = None

        completed_appointments = [
            appointment
            for appointment in appointments
            if appointment.status == "COMPLETED"
        ]

        if completed_appointments:

            patient.last_visit = (
                completed_appointments[0]
            )

        patient.upcoming_appointments = [
            appointment
            for appointment in appointments
            if (
                appointment.appointment_date >= today
                and appointment.status in (
                    "PENDING",
                    "CONFIRMED"
                )
            )
        ]

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context = {

        "patients":
            page_obj,

        "page_obj":
            page_obj,

        "total_patients":
            total_patients,

        "active_patients":
            active_patients,

        "inactive_patients":
            inactive_patients,

        "patients_with_appointments":
            patients_with_appointments,

        "new_patients":
            new_patients,

        "search":
            search,

        "selected_blood_group":
            blood_group,

        "selected_status":
            status,

        "blood_group_choices":
            Patient.BLOOD_GROUP_CHOICES,
    }

    return render(
        request,
        "admin_panel/patients.html",
        context
    )


# ============================================================
# PATIENT - VIEW DETAILS
# ============================================================

@admin_required
def patient_detail(
    request,
    patient_id
):

    patient = get_object_or_404(
        Patient.objects.select_related(
            "user"
        ),
        id=patient_id
    )

    # --------------------------------------------------------
    # APPOINTMENT HISTORY
    # --------------------------------------------------------

    appointments = (
        Appointment.objects
        .filter(
            patient=patient
        )
        .select_related(
            "doctor",
            "doctor__user"
        )
        .order_by(
            "-appointment_date",
            "-appointment_time"
        )
    )

    # --------------------------------------------------------
    # APPOINTMENT STATISTICS
    # --------------------------------------------------------

    total_appointments = appointments.count()

    completed_appointments = appointments.filter(
        status="COMPLETED"
    ).count()

    pending_appointments = appointments.filter(
        status="PENDING"
    ).count()

    confirmed_appointments = appointments.filter(
        status="CONFIRMED"
    ).count()

    cancelled_appointments = appointments.filter(
        status="CANCELLED"
    ).count()

    # --------------------------------------------------------
    # UPCOMING APPOINTMENTS
    # --------------------------------------------------------

    today = timezone.localdate()

    upcoming_appointments = appointments.filter(
        appointment_date__gte=today,
        status__in=[
            "PENDING",
            "CONFIRMED"
        ]
    ).order_by(
        "appointment_date",
        "appointment_time"
    )

    # --------------------------------------------------------
    # PAYMENT HISTORY
    # --------------------------------------------------------

    from appointments.models import PaymentTransaction

    payments = (
        PaymentTransaction.objects
        .filter(
            patient=patient
        )
        .select_related(
            "doctor",
            "doctor__user",
            "appointment"
        )
        .order_by(
            "-created_at"
        )
    )

    total_paid = sum(
        (
            payment.amount
            for payment in payments
            if payment.status == "SUCCESS"
        ),
        Decimal("0.00")
    )

    # --------------------------------------------------------
    # LAST COMPLETED VISIT
    # --------------------------------------------------------

    last_visit = appointments.filter(
        status="COMPLETED"
    ).first()

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context = {

        "patient":
            patient,

        "appointments":
            appointments,

        "upcoming_appointments":
            upcoming_appointments,

        "payments":
            payments,

        "last_visit":
            last_visit,

        "total_appointments":
            total_appointments,

        "completed_appointments":
            completed_appointments,

        "pending_appointments":
            pending_appointments,

        "confirmed_appointments":
            confirmed_appointments,

        "cancelled_appointments":
            cancelled_appointments,

        "total_paid":
            total_paid,
    }

    return render(
        request,
        "admin_panel/patient_detail.html",
        context
    )


# ============================================================
# PATIENT - ADD
# ============================================================

@admin_required
def patient_add(request):
    """
    Create a new Patient and linked User account.
    """

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        first_name = request.POST.get(
            "first_name",
            ""
        ).strip()

        last_name = request.POST.get(
            "last_name",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        phone = request.POST.get(
            "phone",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        confirm_password = request.POST.get(
            "confirm_password",
            ""
        )

        date_of_birth = request.POST.get(
            "date_of_birth",
            ""
        )

        blood_group = request.POST.get(
            "blood_group",
            ""
        )

        allergies = request.POST.get(
            "allergies",
            ""
        ).strip()

        address = request.POST.get(
            "address",
            ""
        ).strip()

        profile_pic = request.FILES.get(
            "profile_pic"
        )

        is_active = (
            request.POST.get("is_active")
            == "on"
        )

        errors = []

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not username:

            errors.append(
                "Username is required."
            )

        if not first_name:

            errors.append(
                "First name is required."
            )

        if not email:

            errors.append(
                "Email address is required."
            )

        if not password:

            errors.append(
                "Password is required."
            )

        if password != confirm_password:

            errors.append(
                "Passwords do not match."
            )

        if not date_of_birth:

            errors.append(
                "Date of birth is required."
            )

        if User.objects.filter(
            username=username
        ).exists():

            errors.append(
                "This username is already in use."
            )

        if email and User.objects.filter(
            email=email
        ).exists():

            errors.append(
                "This email address is already in use."
            )

        valid_blood_groups = {
            choice[0]
            for choice in Patient.BLOOD_GROUP_CHOICES
        }

        if blood_group and blood_group not in valid_blood_groups:

            errors.append(
                "Please select a valid blood group."
            )

        # ----------------------------------------------------
        # VALIDATION ERRORS
        # ----------------------------------------------------

        if errors:

            for error in errors:

                messages.error(
                    request,
                    error
                )

            return render(
                request,
                "admin_panel/patient_form.html",
                {
                    "form_mode": "add",

                    "page_title":
                        "Add Patient",

                    "blood_group_choices":
                        Patient.BLOOD_GROUP_CHOICES,

                    "form_data":
                        request.POST,
                }
            )

        # ----------------------------------------------------
        # CREATE USER + PATIENT
        # ----------------------------------------------------

        try:

            with transaction.atomic():

                user = User.objects.create(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone=phone,
                    role="PATIENT",
                    is_active=is_active,
                )

                user.set_password(
                    password
                )

                user.save()

                patient = Patient.objects.create(
                    user=user,
                    date_of_birth=date_of_birth,
                    blood_group=blood_group,
                    allergies=allergies,
                    address=address,
                    profile_pic=profile_pic,
                )

            messages.success(
                request,
                f"Patient {user.get_full_name() or user.username} "
                "was created successfully."
            )

            return redirect(
                "admin_panel:patient_detail",
                patient_id=patient.id
            )

        except Exception as exc:

            messages.error(
                request,
                f"Unable to create patient: {exc}"
            )

            return render(
                request,
                "admin_panel/patient_form.html",
                {
                    "form_mode": "add",

                    "page_title":
                        "Add Patient",

                    "blood_group_choices":
                        Patient.BLOOD_GROUP_CHOICES,

                    "form_data":
                        request.POST,
                }
            )

    # ========================================================
    # IMPORTANT:
    # GET REQUEST
    # ========================================================
    # This was the missing return causing your ValueError.
    # ========================================================

    return render(
        request,
        "admin_panel/patient_form.html",
        {
            "form_mode": "add",

            "page_title":
                "Add Patient",

            "blood_group_choices":
                Patient.BLOOD_GROUP_CHOICES,

            "form_data":
                {},
        }
    )


# ============================================================
# PATIENT - EDIT
# ============================================================

@admin_required
def patient_edit(
    request,
    patient_id
):
    """
    Update an existing Patient and linked User account.
    """

    patient = get_object_or_404(
        Patient.objects.select_related("user"),
        id=patient_id
    )

    user = patient.user

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        first_name = request.POST.get(
            "first_name",
            ""
        ).strip()

        last_name = request.POST.get(
            "last_name",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        phone = request.POST.get(
            "phone",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        confirm_password = request.POST.get(
            "confirm_password",
            ""
        )

        date_of_birth = request.POST.get(
            "date_of_birth",
            ""
        )

        blood_group = request.POST.get(
            "blood_group",
            ""
        )

        allergies = request.POST.get(
            "allergies",
            ""
        ).strip()

        address = request.POST.get(
            "address",
            ""
        ).strip()

        profile_pic = request.FILES.get(
            "profile_pic"
        )

        is_active = (
            request.POST.get("is_active")
            == "on"
        )

        errors = []

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not username:

            errors.append(
                "Username is required."
            )

        if not first_name:

            errors.append(
                "First name is required."
            )

        if not email:

            errors.append(
                "Email address is required."
            )

        if not date_of_birth:

            errors.append(
                "Date of birth is required."
            )

        if User.objects.filter(
            username=username
        ).exclude(
            id=user.id
        ).exists():

            errors.append(
                "This username is already in use."
            )

        if email and User.objects.filter(
            email=email
        ).exclude(
            id=user.id
        ).exists():

            errors.append(
                "This email address is already in use."
            )

        if password and password != confirm_password:

            errors.append(
                "Passwords do not match."
            )

        valid_blood_groups = {
            choice[0]
            for choice in Patient.BLOOD_GROUP_CHOICES
        }

        if blood_group and blood_group not in valid_blood_groups:

            errors.append(
                "Please select a valid blood group."
            )

        # ----------------------------------------------------
        # VALIDATION ERRORS
        # ----------------------------------------------------

        if errors:

            for error in errors:

                messages.error(
                    request,
                    error
                )

            return render(
                request,
                "admin_panel/patient_form.html",
                {
                    "form_mode": "edit",

                    "page_title":
                        "Edit Patient",

                    "patient":
                        patient,

                    "blood_group_choices":
                        Patient.BLOOD_GROUP_CHOICES,

                    "form_data":
                        request.POST,
                }
            )

        # ----------------------------------------------------
        # UPDATE USER + PATIENT
        # ----------------------------------------------------

        try:

            with transaction.atomic():

                user.username = username

                user.first_name = first_name

                user.last_name = last_name

                user.email = email

                user.phone = phone

                # Patient accounts always remain PATIENT.
                user.role = "PATIENT"

                user.is_active = is_active

                if password:

                    user.set_password(
                        password
                    )

                user.save()

                patient.date_of_birth = (
                    date_of_birth
                )

                patient.blood_group = (
                    blood_group
                )

                patient.allergies = (
                    allergies
                )

                patient.address = (
                    address
                )

                if profile_pic:

                    patient.profile_pic = (
                        profile_pic
                    )

                patient.save()

            messages.success(
                request,
                f"Patient {user.get_full_name() or user.username} "
                "was updated successfully."
            )

            return redirect(
                "admin_panel:patient_detail",
                patient_id=patient.id
            )

        except Exception as exc:

            messages.error(
                request,
                f"Unable to update patient: {exc}"
            )

            return render(
                request,
                "admin_panel/patient_form.html",
                {
                    "form_mode": "edit",

                    "page_title":
                        "Edit Patient",

                    "patient":
                        patient,

                    "blood_group_choices":
                        Patient.BLOOD_GROUP_CHOICES,

                    "form_data":
                        request.POST,
                }
            )

    # ========================================================
    # IMPORTANT:
    # GET REQUEST
    # ========================================================
    # This was also missing and caused the Edit Patient
    # ValueError.
    # ========================================================

    return render(
        request,
        "admin_panel/patient_form.html",
        {
            "form_mode": "edit",

            "page_title":
                "Edit Patient",

            "patient":
                patient,

            "blood_group_choices":
                Patient.BLOOD_GROUP_CHOICES,

            "form_data":
                {},
        }
    )


# ============================================================
# PATIENT - DELETE
# ============================================================

@admin_required
def patient_delete(
    request,
    patient_id
):
    """
    Delete the Patient and linked User account.
    """

    patient = get_object_or_404(
        Patient.objects.select_related("user"),
        id=patient_id
    )

    user = patient.user

    if request.method == "POST":

        patient_name = (
            user.get_full_name()
            or user.username
        )

        try:

            with transaction.atomic():

                # Because Patient.user uses CASCADE,
                # deleting the user also deletes the
                # linked Patient profile.
                user.delete()

            messages.success(
                request,
                f"Patient {patient_name} was permanently deleted."
            )

            return redirect(
                "admin_panel:patients"
            )

        except Exception as exc:

            messages.error(
                request,
                f"Unable to delete patient: {exc}"
            )

            return redirect(
                "admin_panel:patient_detail",
                patient_id=patient.id
            )

    return render(
        request,
        "admin_panel/patient_delete.html",
        {
            "patient":
                patient,
        }
    )

# ============================================================
# DOCTOR - ADD
# ============================================================

@admin_required
def doctor_add(request):
    """
    Create a new Doctor and linked User account.

    This is the dedicated Add Doctor flow from the
    Doctors section of the Admin Panel.
    """

    if request.method == "POST":

        # ----------------------------------------------------
        # ACCOUNT INFORMATION
        # ----------------------------------------------------

        username = request.POST.get(
            "username",
            ""
        ).strip()

        first_name = request.POST.get(
            "first_name",
            ""
        ).strip()

        last_name = request.POST.get(
            "last_name",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        phone = request.POST.get(
            "phone",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        confirm_password = request.POST.get(
            "confirm_password",
            ""
        )

        # ----------------------------------------------------
        # PROFESSIONAL INFORMATION
        # ----------------------------------------------------

        specialization = request.POST.get(
            "specialization",
            ""
        ).strip()

        qualification = request.POST.get(
            "qualification",
            ""
        ).strip()

        experience = request.POST.get(
            "experience",
            ""
        ).strip()

        consultation_fee = request.POST.get(
            "consultation_fee",
            ""
        ).strip()

        rating = request.POST.get(
            "rating",
            "0"
        ).strip()

        # ----------------------------------------------------
        # AVAILABILITY
        # ----------------------------------------------------

        available_days = request.POST.getlist(
            "available_days"
        )

        available_time_start = request.POST.get(
            "available_time_start",
            ""
        ).strip()

        available_time_end = request.POST.get(
            "available_time_end",
            ""
        ).strip()

        is_available = (
            request.POST.get("is_available")
            == "on"
        )

        # ----------------------------------------------------
        # PROFILE
        # ----------------------------------------------------

        profile_pic = request.FILES.get(
            "profile_pic"
        )

        errors = []

        # ====================================================
        # ACCOUNT VALIDATION
        # ====================================================

        if not username:

            errors.append(
                "Username is required."
            )

        if not first_name:

            errors.append(
                "First name is required."
            )

        if not email:

            errors.append(
                "Email address is required."
            )

        if not password:

            errors.append(
                "Password is required."
            )

        if password != confirm_password:

            errors.append(
                "Passwords do not match."
            )

        if User.objects.filter(
            username=username
        ).exists():

            errors.append(
                "This username is already in use."
            )

        if email and User.objects.filter(
            email=email
        ).exists():

            errors.append(
                "This email address is already in use."
            )

        # ====================================================
        # SPECIALIZATION
        # ====================================================

        valid_specializations = {
            choice[0]
            for choice in Doctor.SPECIALIZATION_CHOICES
        }

        if specialization not in valid_specializations:

            errors.append(
                "Please select a valid doctor specialization."
            )

        # ====================================================
        # QUALIFICATION
        # ====================================================

        if not qualification:

            errors.append(
                "Doctor qualification is required."
            )

        # ====================================================
        # EXPERIENCE
        # ====================================================

        experience_value = None

        try:

            experience_value = int(
                experience
            )

            if experience_value < 0:

                errors.append(
                    "Experience cannot be negative."
                )

        except (TypeError, ValueError):

            errors.append(
                "Please enter a valid experience in years."
            )

        # ====================================================
        # CONSULTATION FEE
        # ====================================================

        consultation_fee_value = None

        try:

            consultation_fee_value = Decimal(
                consultation_fee
            )

            if consultation_fee_value < 0:

                errors.append(
                    "Consultation fee cannot be negative."
                )

        except (TypeError, InvalidOperation):

            errors.append(
                "Please enter a valid consultation fee."
            )

        # ====================================================
        # AVAILABLE DAYS
        # ====================================================

        if not available_days:

            errors.append(
                "Please select at least one available day."
            )

        valid_days = {
            choice[0]
            for choice in Doctor.DAYS_CHOICES
        }

        invalid_days = (
            set(available_days)
            - valid_days
        )

        if invalid_days:

            errors.append(
                "Invalid availability day selected."
            )

        # ====================================================
        # AVAILABLE TIME
        # ====================================================

        start_time_value = parse_time(
            available_time_start
        )

        end_time_value = parse_time(
            available_time_end
        )

        if not start_time_value:

            errors.append(
                "Please enter a valid starting time."
            )

        if not end_time_value:

            errors.append(
                "Please enter a valid ending time."
            )

        if (
            start_time_value
            and end_time_value
            and start_time_value >= end_time_value
        ):

            errors.append(
                "Ending time must be later than starting time."
            )

        # ====================================================
        # RATING
        # ====================================================

        rating_value = None

        try:

            rating_value = Decimal(
                rating or "0"
            )

            if (
                rating_value < 0
                or rating_value > 5
            ):

                errors.append(
                    "Rating must be between 0 and 5."
                )

        except (TypeError, InvalidOperation):

            errors.append(
                "Please enter a valid rating."
            )

        # ====================================================
        # VALIDATION ERRORS
        # ====================================================

        if errors:

            for error in errors:

                messages.error(
                    request,
                    error
                )

            return render(
                request,
                "admin_panel/doctor_form.html",
                {
                    "page_title":
                        "Add Doctor",

                    "form_data":
                        request.POST,

                    "specialization_choices":
                        Doctor.SPECIALIZATION_CHOICES,

                    "days_choices":
                        Doctor.DAYS_CHOICES,

                    "selected_days":
                        available_days,
                }
            )

        # ====================================================
        # CREATE USER + DOCTOR
        # ====================================================

        try:

            with transaction.atomic():

                # ------------------------------------------------
                # CREATE USER
                # ------------------------------------------------

                user = User.objects.create(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone=phone,

                    # This page can ONLY create doctors.
                    role="DOCTOR",

                    # New doctors are active by default.
                    is_active=True,
                )

                user.set_password(
                    password
                )

                user.save()

                # ------------------------------------------------
                # CREATE DOCTOR PROFILE
                # ------------------------------------------------

                doctor = Doctor.objects.create(
                    user=user,

                    specialization=specialization,

                    qualification=qualification,

                    experience=experience_value,

                    consultation_fee=consultation_fee_value,

                    available_days=",".join(
                        available_days
                    ),

                    available_time_start=start_time_value,

                    available_time_end=end_time_value,

                    profile_pic=profile_pic,

                    rating=rating_value,

                    is_available=is_available,
                )

            messages.success(
                request,
                f"Dr. {user.get_full_name() or user.username} "
                "was added successfully."
            )

            return redirect(
                "admin_panel:doctors"
            )

        except Exception as exc:

            messages.error(
                request,
                f"Unable to add doctor: {exc}"
            )

            return render(
                request,
                "admin_panel/doctor_form.html",
                {
                    "page_title":
                        "Add Doctor",

                    "form_data":
                        request.POST,

                    "specialization_choices":
                        Doctor.SPECIALIZATION_CHOICES,

                    "days_choices":
                        Doctor.DAYS_CHOICES,

                    "selected_days":
                        available_days,
                }
            )

    # ========================================================
    # GET REQUEST
    # ========================================================

    return render(
        request,
        "admin_panel/doctor_form.html",
        {
            "page_title":
                "Add Doctor",

            "form_data":
                {},

            "specialization_choices":
                Doctor.SPECIALIZATION_CHOICES,

            "days_choices":
                Doctor.DAYS_CHOICES,

            "selected_days":
                [],
        }
    )