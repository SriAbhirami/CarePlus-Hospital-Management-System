from datetime import datetime
import uuid

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect

from doctors.models import Doctor
from patients.models import Patient

from appointments.models import (
    Appointment,
    PaymentTransaction,
    PaymentDetails,
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

        # ----------------------------------------------------
        # VALIDATE PAYMENT METHOD
        # ----------------------------------------------------

        valid_methods = {
            choice[0]
            for choice in
            PaymentTransaction.PAYMENT_METHOD_CHOICES
        }

        if payment_method not in valid_methods:

            return render(
                request,
                'patient/pay_bills.html',
                {
                    'doctor': doctor,
                    'pending_booking': pending_booking,
                    'error': (
                        'Please select a valid payment method.'
                    )
                }
            )

        # ----------------------------------------------------
        # STORE PAYMENT METHOD
        # ----------------------------------------------------

        pending_booking[
            'payment_method'
        ] = payment_method

        # Remove any previous payment details if
        # the patient comes back and changes method.
        pending_booking.pop(
            'payment_details',
            None
        )

        request.session[
            'pending_booking'
        ] = pending_booking

        request.session.modified = True

        # ----------------------------------------------------
        # GO TO PAYMENT DETAILS
        # ----------------------------------------------------

        return redirect(
            'payment_details'
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
# PAYMENT DETAILS
# ============================================================

@login_required
def payment_details(request):

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
    # GET PAYMENT METHOD
    # --------------------------------------------------------

    payment_method = pending_booking.get(
        'payment_method'
    )

    valid_methods = {
        choice[0]
        for choice in
        PaymentTransaction.PAYMENT_METHOD_CHOICES
    }

    if payment_method not in valid_methods:

        return redirect(
            'pay_bills'
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

    # ========================================================
    # FORM SUBMISSION
    # ========================================================

    if request.method == 'POST':

        payment_data = {}

        # ====================================================
        # UPI
        # ====================================================

        if payment_method == 'UPI':

            upi_id = (
                request.POST.get(
                    'upi_id'
                )
                or ''
            ).strip()

            if not upi_id:

                return render(
                    request,
                    'patient/payment_details.html',
                    {
                        'doctor': doctor,
                        'pending_booking': pending_booking,
                        'payment_method': payment_method,
                        'error': 'Please enter your UPI ID.'
                    }
                )

            # Simple demo validation.
            # Example: abhirami@upi
            if (
                '@' not in upi_id
                or upi_id.startswith('@')
                or upi_id.endswith('@')
            ):

                return render(
                    request,
                    'patient/payment_details.html',
                    {
                        'doctor': doctor,
                        'pending_booking': pending_booking,
                        'payment_method': payment_method,
                        'error': (
                            'Please enter a valid UPI ID, '
                            'for example name@upi.'
                        )
                    }
                )

            payment_data = {
                'upi_id': upi_id
            }

        # ====================================================
        # CARD
        # ====================================================

        elif payment_method == 'CARD':

            card_number = (
                request.POST.get(
                    'card_number'
                )
                or ''
            ).replace(
                ' ',
                ''
            ).strip()

            card_holder_name = (
                request.POST.get(
                    'card_holder_name'
                )
                or ''
            ).strip()

            expiry_month = (
                request.POST.get(
                    'expiry_month'
                )
                or ''
            ).strip()

            expiry_year = (
                request.POST.get(
                    'expiry_year'
                )
                or ''
            ).strip()

            cvv = (
                request.POST.get(
                    'cvv'
                )
                or ''
            ).strip()

            # ------------------------------------------------
            # CARD NUMBER
            # ------------------------------------------------

            if (
                not card_number
                or not card_number.isdigit()
                or not 12 <= len(card_number) <= 19
            ):

                return render(
                    request,
                    'patient/payment_details.html',
                    {
                        'doctor': doctor,
                        'pending_booking': pending_booking,
                        'payment_method': payment_method,
                        'error': (
                            'Please enter a valid card number.'
                        )
                    }
                )

            # ------------------------------------------------
            # CARD HOLDER
            # ------------------------------------------------

            if not card_holder_name:

                return render(
                    request,
                    'patient/payment_details.html',
                    {
                        'doctor': doctor,
                        'pending_booking': pending_booking,
                        'payment_method': payment_method,
                        'error': (
                            'Please enter the card holder name.'
                        )
                    }
                )

            # ------------------------------------------------
            # EXPIRY
            # ------------------------------------------------

            try:

                expiry_month_int = int(
                    expiry_month
                )

                expiry_year_int = int(
                    expiry_year
                )

            except ValueError:

                return render(
                    request,
                    'patient/payment_details.html',
                    {
                        'doctor': doctor,
                        'pending_booking': pending_booking,
                        'payment_method': payment_method,
                        'error': (
                            'Please enter a valid expiry date.'
                        )
                    }
                )

            if not 1 <= expiry_month_int <= 12:

                return render(
                    request,
                    'patient/payment_details.html',
                    {
                        'doctor': doctor,
                        'pending_booking': pending_booking,
                        'payment_method': payment_method,
                        'error': (
                            'Expiry month must be between 01 and 12.'
                        )
                    }
                )

            if not 2026 <= expiry_year_int <= 2100:

                return render(
                    request,
                    'patient/payment_details.html',
                    {
                        'doctor': doctor,
                        'pending_booking': pending_booking,
                        'payment_method': payment_method,
                        'error': (
                            'Please enter a valid expiry year.'
                        )
                    }
                )

            # ------------------------------------------------
            # CVV
            # ------------------------------------------------

            if (
                not cvv
                or not cvv.isdigit()
                or len(cvv) not in [3, 4]
            ):

                return render(
                    request,
                    'patient/payment_details.html',
                    {
                        'doctor': doctor,
                        'pending_booking': pending_booking,
                        'payment_method': payment_method,
                        'error': (
                            'Please enter a valid 3 or 4 digit CVV.'
                        )
                    }
                )

            # ------------------------------------------------
            # IMPORTANT:
            # Never store full card number or CVV.
            # Only store the last 4 digits.
            # ------------------------------------------------

            payment_data = {
                'card_holder_name': card_holder_name,
                'card_last4': card_number[-4:],
                'expiry_month': expiry_month_int,
                'expiry_year': expiry_year_int,
            }

        # ====================================================
        # NET BANKING
        # ====================================================

        elif payment_method == 'NET_BANKING':

            bank_name = (
                request.POST.get(
                    'bank_name'
                )
                or ''
            ).strip()

            bank_customer_id = (
                request.POST.get(
                    'bank_customer_id'
                )
                or ''
            ).strip()

            if not bank_name:

                return render(
                    request,
                    'patient/payment_details.html',
                    {
                        'doctor': doctor,
                        'pending_booking': pending_booking,
                        'payment_method': payment_method,
                        'error': 'Please select your bank.'
                    }
                )

            if not bank_customer_id:

                return render(
                    request,
                    'patient/payment_details.html',
                    {
                        'doctor': doctor,
                        'pending_booking': pending_booking,
                        'payment_method': payment_method,
                        'error': (
                            'Please enter your customer ID.'
                        )
                    }
                )

            payment_data = {
                'bank_name': bank_name,
                'bank_customer_id': bank_customer_id,
            }

        # ====================================================
        # STORE SAFE DETAILS IN SESSION
        # ====================================================

        pending_booking[
            'payment_details'
        ] = payment_data

        request.session[
            'pending_booking'
        ] = pending_booking

        request.session.modified = True

        return redirect(
            'process_payment'
        )

    # ========================================================
    # DISPLAY PAYMENT DETAILS PAGE
    # ========================================================

    return render(
        request,
        'patient/payment_details.html',
        {
            'doctor': doctor,
            'pending_booking': pending_booking,
            'payment_method': payment_method,
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

    # --------------------------------------------------------
    # PAYMENT DETAILS
    # --------------------------------------------------------

    saved_payment_details = pending_booking.get(
        'payment_details'
    )

    if not saved_payment_details:

        return redirect(
            'payment_details'
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

            transaction_id = (
                'CP'
                + uuid.uuid4().hex[:12].upper()
            )

            # ------------------------------------------------
            # CREATE ALL SUCCESSFUL PAYMENT RECORDS TOGETHER
            # ------------------------------------------------

            with transaction.atomic():

                appointment = Appointment.objects.create(

                    patient=patient,

                    doctor=doctor,

                    appointment_date=appointment_date,

                    appointment_time=appointment_time,

                    consultation_fee=doctor.consultation_fee,

                    status='CONFIRMED'
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

                payment_transaction = (
                    PaymentTransaction.objects.get(
                        transaction_id=transaction_id
                    )
                )

                PaymentDetails.objects.create(
                    transaction=payment_transaction,
                    **saved_payment_details
                )

            # ------------------------------------------------
            # STORE SUCCESS INFORMATION
            # ------------------------------------------------

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

            # ------------------------------------------------
            # CREATE DECLINED PAYMENT RECORDS TOGETHER
            # ------------------------------------------------

            with transaction.atomic():

                payment_transaction = (
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
                )

                PaymentDetails.objects.create(
                    transaction=payment_transaction,
                    **saved_payment_details
                )

            # ------------------------------------------------
            # STORE FAILURE INFORMATION
            # ------------------------------------------------

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