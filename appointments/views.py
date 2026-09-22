from datetime import datetime
import uuid

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from doctors.models import Doctor
from patients.models import Patient

from appointments.models import (
    Appointment,
    PaymentTransaction,
)


# ============================================================
# BOOK APPOINTMENT
# ============================================================

@login_required
def book_appointment(request):

    # --------------------------------------------------------
    # CHECK PATIENT PROFILE
    # --------------------------------------------------------

    try:

        patient = request.user.patient_profile

    except Patient.DoesNotExist:

        return redirect(
            'patient_dashboard'
        )

    # --------------------------------------------------------
    # SPECIALIZATIONS
    # --------------------------------------------------------

    specializations = Doctor.SPECIALIZATION_CHOICES

    # --------------------------------------------------------
    # GET SELECTED SPECIALIZATION
    # --------------------------------------------------------

    specialization = (
        request.GET.get('specialization')
        or request.POST.get('specialization')
    )

    # --------------------------------------------------------
    # GET SELECTED DOCTOR
    #
    # IMPORTANT:
    # Doctor can come from:
    #   1. GET  -> when coming from Doctors/Specialization page
    #   2. POST -> when submitting booking form
    # --------------------------------------------------------

    doctor_id = (
        request.GET.get('doctor')
        or request.POST.get('doctor')
    )

    selected_doctor = None

    if doctor_id:

        try:

            selected_doctor = (
                Doctor.objects
                .select_related('user')
                .get(
                    id=doctor_id,
                    is_available=True
                )
            )

            # Automatically use the doctor's specialization
            # when a specific doctor was selected.
            specialization = selected_doctor.specialization

        except (
            Doctor.DoesNotExist,
            ValueError
        ):

            selected_doctor = None

    # --------------------------------------------------------
    # GET AVAILABLE DOCTORS
    # --------------------------------------------------------

    doctors = (
        Doctor.objects
        .filter(
            is_available=True
        )
        .select_related('user')
    )

    if specialization:

        doctors = doctors.filter(
            specialization=specialization
        )

    # ========================================================
    # POST ACTIONS
    # ========================================================

    if request.method == 'POST':

        action = request.POST.get(
            'action'
        )

        # ====================================================
        # CONTINUE
        # ====================================================

        if action == 'continue':

            if not selected_doctor:

                return render(
                    request,
                    'patient/book_appointment.html',
                    {
                        'specializations': specializations,
                        'doctors': doctors,
                        'selected_doctor': selected_doctor,
                        'specialization': specialization,
                        'error': 'Please select a doctor.'
                    }
                )

            return render(
                request,
                'patient/book_appointment.html',
                {
                    'specializations': specializations,
                    'doctors': doctors,
                    'selected_doctor': selected_doctor,
                    'specialization': specialization,
                    'show_date_time': True
                }
            )

        # ====================================================
        # CONFIRM BOOKING
        # ====================================================

        elif action == 'confirm_booking':

            appointment_date = request.POST.get(
                'appointment_date'
            )

            appointment_time = request.POST.get(
                'appointment_time'
            )

            # ------------------------------------------------
            # VALIDATE DOCTOR
            # ------------------------------------------------

            if not selected_doctor:

                return render(
                    request,
                    'patient/book_appointment.html',
                    {
                        'specializations': specializations,
                        'doctors': doctors,
                        'selected_doctor': selected_doctor,
                        'specialization': specialization,
                        'error': 'Please select a valid doctor.'
                    }
                )

            # ------------------------------------------------
            # VALIDATE DATE
            # ------------------------------------------------

            if not appointment_date:

                return render(
                    request,
                    'patient/book_appointment.html',
                    {
                        'specializations': specializations,
                        'doctors': doctors,
                        'selected_doctor': selected_doctor,
                        'specialization': specialization,
                        'show_date_time': True,
                        'error': (
                            'Please select an appointment date.'
                        )
                    }
                )

            # ------------------------------------------------
            # VALIDATE TIME
            # ------------------------------------------------

            if not appointment_time:

                return render(
                    request,
                    'patient/book_appointment.html',
                    {
                        'specializations': specializations,
                        'doctors': doctors,
                        'selected_doctor': selected_doctor,
                        'specialization': specialization,
                        'show_date_time': True,
                        'error': (
                            'Please select an appointment time.'
                        )
                    }
                )

            # ------------------------------------------------
            # CONVERT DATE
            # ------------------------------------------------

            try:

                selected_date = datetime.strptime(
                    appointment_date,
                    '%Y-%m-%d'
                ).date()

            except ValueError:

                return render(
                    request,
                    'patient/book_appointment.html',
                    {
                        'specializations': specializations,
                        'doctors': doctors,
                        'selected_doctor': selected_doctor,
                        'specialization': specialization,
                        'show_date_time': True,
                        'error': 'Invalid appointment date.'
                    }
                )

            # ------------------------------------------------
            # CHECK AVAILABLE DAY
            # ------------------------------------------------

            weekday_map = {
                0: 'MON',
                1: 'TUE',
                2: 'WED',
                3: 'THU',
                4: 'FRI',
                5: 'SAT',
                6: 'SUN',
            }

            selected_day = weekday_map[
                selected_date.weekday()
            ]

            available_days = [
                day.strip().upper()
                for day in
                selected_doctor.available_days.split(',')
            ]

            if selected_day not in available_days:

                return render(
                    request,
                    'patient/book_appointment.html',
                    {
                        'specializations': specializations,
                        'doctors': doctors,
                        'selected_doctor': selected_doctor,
                        'specialization': specialization,
                        'show_date_time': True,
                        'error': (
                            'The selected doctor is not available '
                            'on this day.'
                        )
                    }
                )

            # ------------------------------------------------
            # CONVERT TIME
            # ------------------------------------------------

            try:

                selected_time = datetime.strptime(
                    appointment_time,
                    '%H:%M'
                ).time()

            except ValueError:

                return render(
                    request,
                    'patient/book_appointment.html',
                    {
                        'specializations': specializations,
                        'doctors': doctors,
                        'selected_doctor': selected_doctor,
                        'specialization': specialization,
                        'show_date_time': True,
                        'error': 'Invalid appointment time.'
                    }
                )

            # ------------------------------------------------
            # CHECK DOCTOR AVAILABLE TIME
            # ------------------------------------------------

            if not (
                selected_doctor.available_time_start
                <= selected_time
                <= selected_doctor.available_time_end
            ):

                return render(
                    request,
                    'patient/book_appointment.html',
                    {
                        'specializations': specializations,
                        'doctors': doctors,
                        'selected_doctor': selected_doctor,
                        'specialization': specialization,
                        'show_date_time': True,
                        'error': (
                            'The selected time is outside '
                            "the doctor's available hours."
                        )
                    }
                )

            # ------------------------------------------------
            # CHECK EXISTING SLOT
            # ------------------------------------------------

            slot_exists = Appointment.objects.filter(
                doctor=selected_doctor,
                appointment_date=selected_date,
                appointment_time=selected_time,
                status__in=[
                    'PENDING',
                    'CONFIRMED'
                ]
            ).exists()

            if slot_exists:

                return render(
                    request,
                    'patient/book_appointment.html',
                    {
                        'specializations': specializations,
                        'doctors': doctors,
                        'selected_doctor': selected_doctor,
                        'specialization': specialization,
                        'show_date_time': True,
                        'error': (
                            'This time slot is already booked. '
                            'Please select another time.'
                        )
                    }
                )

            # ------------------------------------------------
            # STORE TEMPORARY BOOKING
            # ------------------------------------------------

            request.session[
                'pending_booking'
            ] = {

                'doctor_id': selected_doctor.id,

                'appointment_date': appointment_date,

                'appointment_time': appointment_time,

                'consultation_fee': str(
                    selected_doctor.consultation_fee
                ),
            }

            request.session.modified = True

            # ------------------------------------------------
            # GO TO PAYMENT
            # ------------------------------------------------

            return redirect(
                'pay_bills'
            )

    # ========================================================
    # NORMAL PAGE LOAD
    # ========================================================

    return render(
        request,
        'patient/book_appointment.html',
        {
            'specializations': specializations,
            'doctors': doctors,
            'selected_doctor': selected_doctor,
            'specialization': specialization,
        }
    )


# ============================================================
# PAYMENT / BILLS
# ============================================================

@login_required
def pay_bills(request):

    # --------------------------------------------------------
    # CHECK PATIENT PROFILE
    # --------------------------------------------------------

    try:

        patient = request.user.patient_profile

    except Patient.DoesNotExist:

        return redirect(
            'patient_dashboard'
        )

    # --------------------------------------------------------
    # GET PENDING BOOKING
    # --------------------------------------------------------

    pending_booking = request.session.get(
        'pending_booking'
    )

    if not pending_booking:

        return redirect(
            'book_appointment'
        )

    # --------------------------------------------------------
    # GET DOCTOR
    # --------------------------------------------------------

    try:

        doctor = Doctor.objects.get(
            id=pending_booking['doctor_id']
        )

    except Doctor.DoesNotExist:

        request.session.pop(
            'pending_booking',
            None
        )

        request.session.modified = True

        return redirect(
            'book_appointment'
        )

    # --------------------------------------------------------
    # PAYMENT SUBMISSION
    # --------------------------------------------------------

    if request.method == 'POST':

        payment_method = request.POST.get(
            'payment_method'
        )

        if not payment_method:

            return render(
                request,
                'patient/pay_bills.html',
                {
                    'doctor': doctor,
                    'pending_booking': pending_booking,
                    'error': (
                        'Please select a payment method.'
                    )
                }
            )

        request.session[
            'pending_booking'
        ]['payment_method'] = payment_method

        request.session.modified = True

        return redirect(
            'process_payment'
        )

    # --------------------------------------------------------
    # DISPLAY PAYMENT PAGE
    # --------------------------------------------------------

    return render(
        request,
        'patient/pay_bills.html',
        {
            'doctor': doctor,
            'pending_booking': pending_booking,
        }
    )


# ============================================================
# PROCESS PAYMENT
# ============================================================

@login_required
def process_payment(request):

    # --------------------------------------------------------
    # CHECK PATIENT PROFILE
    # --------------------------------------------------------

    try:

        patient = request.user.patient_profile

    except Patient.DoesNotExist:

        return redirect(
            'patient_dashboard'
        )

    # --------------------------------------------------------
    # GET PENDING BOOKING
    # --------------------------------------------------------

    pending_booking = request.session.get(
        'pending_booking'
    )

    if not pending_booking:

        return redirect(
            'book_appointment'
        )

    # --------------------------------------------------------
    # GET DOCTOR
    # --------------------------------------------------------

    try:

        doctor = Doctor.objects.get(
            id=pending_booking['doctor_id']
        )

    except Doctor.DoesNotExist:

        request.session.pop(
            'pending_booking',
            None
        )

        request.session.modified = True

        return redirect(
            'book_appointment'
        )

    # --------------------------------------------------------
    # PAYMENT METHOD
    # --------------------------------------------------------

    payment_method = pending_booking.get(
        'payment_method'
    )

    if not payment_method:

        return redirect(
            'pay_bills'
        )

    # ========================================================
    # PAYMENT SUBMISSION
    # ========================================================

    if request.method == 'POST':

        payment_result = request.POST.get(
            'payment_result'
        )

        # ----------------------------------------------------
        # CONVERT DATE AND TIME
        # ----------------------------------------------------

        try:

            appointment_date = datetime.strptime(
                pending_booking['appointment_date'],
                '%Y-%m-%d'
            ).date()

            appointment_time = datetime.strptime(
                pending_booking['appointment_time'],
                '%H:%M'
            ).time()

        except (
            ValueError,
            KeyError,
            TypeError
        ):

            request.session.pop(
                'pending_booking',
                None
            )

            request.session.modified = True

            return redirect(
                'book_appointment'
            )

        # ====================================================
        # SUCCESSFUL PAYMENT
        # ====================================================

        if payment_result == 'success':

            appointment = Appointment.objects.create(

                patient=patient,

                doctor=doctor,

                appointment_date=appointment_date,

                appointment_time=appointment_time,

                consultation_fee=doctor.consultation_fee,

                status='CONFIRMED'
            )

            transaction_id = (
                'CP'
                + uuid.uuid4().hex[:12].upper()
            )

            PaymentTransaction.objects.create(

                patient=patient,

                doctor=doctor,

                appointment=appointment,

                amount=doctor.consultation_fee,

                payment_method=payment_method,

                status='SUCCESS',

                transaction_id=transaction_id,

                appointment_date=appointment_date,

                appointment_time=appointment_time,
            )

            request.session[
                'payment_success'
            ] = {

                'appointment_id': appointment.id,

                'transaction_id': transaction_id,

                'doctor_name': (
                    doctor.user.get_full_name()
                    or doctor.user.username
                ),

                'appointment_date': (
                    pending_booking[
                        'appointment_date'
                    ]
                ),

                'appointment_time': (
                    pending_booking[
                        'appointment_time'
                    ]
                ),

                'consultation_fee': str(
                    doctor.consultation_fee
                ),

                'payment_method': payment_method,
            }

            request.session.pop(
                'pending_booking',
                None
            )

            request.session.modified = True

            return redirect(
                'payment_success'
            )

        # ====================================================
        # DECLINED PAYMENT
        # ====================================================

        elif payment_result == 'declined':

            transaction_id = (
                'CP'
                + uuid.uuid4().hex[:12].upper()
            )

            PaymentTransaction.objects.create(

                patient=patient,

                doctor=doctor,

                appointment=None,

                amount=doctor.consultation_fee,

                payment_method=payment_method,

                status='DECLINED',

                transaction_id=transaction_id,

                appointment_date=appointment_date,

                appointment_time=appointment_time,
            )

            request.session[
                'payment_failed'
            ] = {

                'transaction_id': transaction_id,

                'doctor_name': (
                    doctor.user.get_full_name()
                    or doctor.user.username
                ),

                'appointment_date': (
                    pending_booking[
                        'appointment_date'
                    ]
                ),

                'appointment_time': (
                    pending_booking[
                        'appointment_time'
                    ]
                ),

                'consultation_fee': str(
                    doctor.consultation_fee
                ),

                'payment_method': payment_method,
            }

            request.session.pop(
                'pending_booking',
                None
            )

            request.session.modified = True

            return redirect(
                'payment_declined'
            )

    # ========================================================
    # PAYMENT PROCESSING PAGE
    # ========================================================

    return render(
        request,
        'patient/process_payment.html',
        {
            'doctor': doctor,
            'pending_booking': pending_booking,
            'payment_method': payment_method,
        }
    )


# ============================================================
# PAYMENT SUCCESS
# ============================================================

@login_required
def payment_success(request):

    payment_success = request.session.get(
        'payment_success'
    )

    if not payment_success:

        return redirect(
            'patient_dashboard'
        )

    return render(
        request,
        'patient/payment_success.html',
        {
            'payment_success': payment_success
        }
    )


# ============================================================
# PAYMENT DECLINED
# ============================================================

@login_required
def payment_declined(request):

    payment_failed = request.session.get(
        'payment_failed'
    )

    if not payment_failed:

        return redirect(
            'patient_dashboard'
        )

    return render(
        request,
        'patient/payment_declined.html',
        {
            'payment_failed': payment_failed
        }
    )