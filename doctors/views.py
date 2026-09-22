from datetime import datetime
from io import BytesIO

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse

from doctors.models import Doctor

from appointments.models import (
    Appointment,
    Prescription,
    PrescriptionMedicine,
)

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle
)
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


# ============================================================
# DOCTOR DASHBOARD
# ============================================================

def doctor_dashboard(request):

    doctor = request.user.doctor_profile

    # --------------------------------------------------------
    # HANDLE DOCTOR PROFILE PHOTO UPLOAD
    # --------------------------------------------------------

    if request.method == 'POST':

        profile_pic = request.FILES.get('profile_pic')

        if profile_pic:

            doctor.profile_pic = profile_pic

            doctor.save(
                update_fields=['profile_pic']
            )

            return redirect('doctor_dashboard')

    # --------------------------------------------------------
    # GET DOCTOR APPOINTMENTS
    # --------------------------------------------------------

    appointments = Appointment.objects.filter(
        doctor=doctor
    ).order_by(
        'appointment_date',
        'appointment_time'
    )

    # --------------------------------------------------------
    # TODAY'S APPOINTMENTS
    # --------------------------------------------------------

    today = datetime.today().date()

    today_appointments = appointments.filter(
        appointment_date=today
    )

    # --------------------------------------------------------
    # STATISTICS
    # --------------------------------------------------------

    pending_appointments = appointments.filter(
        status='PENDING'
    )

    completed_appointments = appointments.filter(
        status='COMPLETED'
    )

    total_patients = appointments.values(
        'patient'
    ).distinct().count()

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render(
        request,
        'doctor/dashboard.html',
        {
            'doctor': doctor,
            'appointments': appointments,
            'today_appointments': today_appointments,
            'pending_appointments': pending_appointments,
            'completed_appointments': completed_appointments,
            'total_patients': total_patients,
        }
    )


# ============================================================
# DOCTOR APPOINTMENTS
# ============================================================

def doctor_appointments(request):

    doctor = request.user.doctor_profile

    status_filter = request.GET.get(
        'status',
        'ALL'
    )

    appointments = Appointment.objects.filter(
        doctor=doctor
    ).order_by(
        '-appointment_date',
        '-appointment_time'
    )

    if status_filter != 'ALL':

        appointments = appointments.filter(
            status=status_filter
        )

    return render(
        request,
        'doctor/appointments.html',
        {
            'doctor': doctor,
            'appointments': appointments,
            'status_filter': status_filter,
        }
    )


# ============================================================
# CREATE PRESCRIPTION
# ============================================================

def create_prescription(
    request,
    appointment_id
):

    doctor = request.user.doctor_profile

    # --------------------------------------------------------
    # GET APPOINTMENT
    # --------------------------------------------------------

    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        doctor=doctor
    )

    # --------------------------------------------------------
    # CHECK EXISTING PRESCRIPTION
    # --------------------------------------------------------

    if hasattr(
        appointment,
        'prescription'
    ):

        messages.info(
            request,
            'A prescription already exists for this appointment.'
        )

        return redirect(
            'doctor_prescription_detail',
            prescription_id=appointment.prescription.id
        )

    # --------------------------------------------------------
    # HANDLE FORM SUBMISSION
    # --------------------------------------------------------

    if request.method == 'POST':

        diagnosis = request.POST.get(
            'diagnosis',
            ''
        ).strip()

        notes = request.POST.get(
            'notes',
            ''
        ).strip()

        # ----------------------------------------------------
        # CREATE PRESCRIPTION
        # ----------------------------------------------------

        prescription = Prescription.objects.create(
            appointment=appointment,
            diagnosis=diagnosis,
            notes=notes
        )

        # ----------------------------------------------------
        # GET MEDICINE DATA
        # ----------------------------------------------------

        medicine_names = request.POST.getlist(
            'medicine_name'
        )

        dosages = request.POST.getlist(
            'dosage'
        )

        frequencies = request.POST.getlist(
            'frequency'
        )

        durations = request.POST.getlist(
            'duration'
        )

        instructions = request.POST.getlist(
            'medicine_instructions'
        )

        # ----------------------------------------------------
        # CREATE MEDICINES
        # ----------------------------------------------------

        for i in range(
            len(medicine_names)
        ):

            medicine_name = (
                medicine_names[i].strip()
            )

            if not medicine_name:
                continue

            dosage = (
                dosages[i].strip()
                if i < len(dosages)
                else ''
            )

            frequency = (
                frequencies[i].strip()
                if i < len(frequencies)
                else ''
            )

            duration = (
                durations[i].strip()
                if i < len(durations)
                else ''
            )

            medicine_instruction = (
                instructions[i].strip()
                if i < len(instructions)
                else ''
            )

            PrescriptionMedicine.objects.create(
                prescription=prescription,
                medicine_name=medicine_name,
                dosage=dosage,
                frequency=frequency,
                duration=duration,
                instructions=medicine_instruction
            )

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        messages.success(
            request,
            'Prescription created successfully.'
        )

        return redirect(
            'doctor_prescription_detail',
            prescription_id=prescription.id
        )

    # --------------------------------------------------------
    # DISPLAY PAGE
    # --------------------------------------------------------

    return render(
        request,
        'doctor/create_prescription.html',
        {
            'doctor': doctor,
            'appointment': appointment,
        }
    )


# ============================================================
# DOCTOR PRESCRIPTIONS
# ============================================================

def doctor_prescriptions(request):

    doctor = request.user.doctor_profile

    appointments = (
        Appointment.objects
        .filter(
            doctor=doctor
        )
        .select_related(
            'patient__user'
        )
        .order_by(
            '-appointment_date',
            '-appointment_time'
        )
    )

    return render(
        request,
        'doctor/prescriptions.html',
        {
            'doctor': doctor,
            'appointments': appointments,
        }
    )


# ============================================================
# DOCTOR PRESCRIPTION DETAIL
# ============================================================

def doctor_prescription_detail(
    request,
    prescription_id
):

    doctor = request.user.doctor_profile

    prescription = get_object_or_404(
        Prescription.objects
        .select_related(
            'appointment__patient__user',
            'appointment__doctor__user'
        )
        .prefetch_related(
            'medicines'
        ),
        id=prescription_id,
        appointment__doctor=doctor
    )

    return render(
        request,
        'doctor/prescription_detail.html',
        {
            'doctor': doctor,
            'prescription': prescription,
        }
    )


# ============================================================
# DOCTOR DOWNLOAD PRESCRIPTION PDF
# ============================================================

def download_prescription_pdf(
    request,
    prescription_id
):

    doctor = request.user.doctor_profile

    prescription = get_object_or_404(
        Prescription.objects
        .select_related(
            'appointment__patient__user',
            'appointment__doctor__user'
        )
        .prefetch_related(
            'medicines'
        ),
        id=prescription_id,
        appointment__doctor=doctor
    )

    # --------------------------------------------------------
    # CREATE PDF IN MEMORY
    # --------------------------------------------------------

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    styles = getSampleStyleSheet()

    # --------------------------------------------------------
    # STYLES
    # --------------------------------------------------------

    hospital_style = ParagraphStyle(
        'HospitalStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#132238'),
        alignment=TA_CENTER,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#6B7280'),
        alignment=TA_CENTER,
        spaceAfter=12,
    )

    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1769AA'),
        alignment=TA_LEFT,
        spaceAfter=10,
    )

    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#172033'),
        spaceBefore=8,
        spaceAfter=7,
    )

    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#374151'),
    )

    small_style = ParagraphStyle(
        'SmallStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#6B7280'),
    )

    medicine_style = ParagraphStyle(
        'MedicineStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#172033'),
    )

    # --------------------------------------------------------
    # PDF CONTENT
    # --------------------------------------------------------

    story = []

    story.append(
        Paragraph(
            'CAREPLUS HOSPITAL',
            hospital_style
        )
    )

    story.append(
        Paragraph(
            'Healthcare Management System',
            subtitle_style
        )
    )

    header_line = Table(
        [['']],
        colWidths=[174 * mm],
        rowHeights=[1 * mm]
    )

    header_line.setStyle(
        TableStyle([
            (
                'BACKGROUND',
                (0, 0),
                (-1, -1),
                colors.HexColor('#1769AA')
            ),
        ])
    )

    story.append(header_line)
    story.append(Spacer(1, 8))

    story.append(
        Paragraph(
            'MEDICAL PRESCRIPTION',
            title_style
        )
    )

    prescription_number = (
        f'RX-{prescription.id:05d}'
    )

    prescription_info = [
        [
            Paragraph(
                '<b>Prescription No.</b>',
                normal_style
            ),
            Paragraph(
                prescription_number,
                normal_style
            ),
            Paragraph(
                '<b>Issued On</b>',
                normal_style
            ),
            Paragraph(
                prescription.created_at.strftime(
                    '%d %b %Y, %I:%M %p'
                ),
                normal_style
            ),
        ]
    ]

    prescription_table = Table(
        prescription_info,
        colWidths=[
            32 * mm,
            52 * mm,
            28 * mm,
            62 * mm
        ]
    )

    prescription_table.setStyle(
        TableStyle([
            (
                'BACKGROUND',
                (0, 0),
                (-1, -1),
                colors.HexColor('#F7F9FB')
            ),
            (
                'BOX',
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor('#E5E9EF')
            ),
            (
                'INNERGRID',
                (0, 0),
                (-1, -1),
                0.3,
                colors.HexColor('#E5E9EF')
            ),
            (
                'VALIGN',
                (0, 0),
                (-1, -1),
                'MIDDLE'
            ),
            (
                'LEFTPADDING',
                (0, 0),
                (-1, -1),
                7
            ),
            (
                'RIGHTPADDING',
                (0, 0),
                (-1, -1),
                7
            ),
            (
                'TOPPADDING',
                (0, 0),
                (-1, -1),
                7
            ),
            (
                'BOTTOMPADDING',
                (0, 0),
                (-1, -1),
                7
            ),
        ])
    )

    story.append(prescription_table)
    story.append(Spacer(1, 12))

    # --------------------------------------------------------
    # PATIENT & APPOINTMENT INFORMATION
    # --------------------------------------------------------

    story.append(
        Paragraph(
            'PATIENT & APPOINTMENT INFORMATION',
            section_style
        )
    )

    patient = prescription.appointment.patient
    patient_user = patient.user
    appointment = prescription.appointment

    patient_name = (
        patient_user.get_full_name()
        or patient_user.username
    )

    doctor_name = (
        appointment.doctor.user.get_full_name()
        or appointment.doctor.user.username
    )

    specialization = (
        appointment.doctor.get_specialization_display()
    )

    patient_info = [
        [
            Paragraph(
                '<b>Patient</b>',
                normal_style
            ),
            Paragraph(
                patient_name,
                normal_style
            ),
            Paragraph(
                '<b>Doctor</b>',
                normal_style
            ),
            Paragraph(
                f'Dr. {doctor_name}',
                normal_style
            ),
        ],
        [
            Paragraph(
                '<b>Specialization</b>',
                normal_style
            ),
            Paragraph(
                specialization,
                normal_style
            ),
            Paragraph(
                '<b>Appointment Date</b>',
                normal_style
            ),
            Paragraph(
                appointment.appointment_date.strftime(
                    '%d %b %Y'
                ),
                normal_style
            ),
        ],
        [
            Paragraph(
                '<b>Appointment Time</b>',
                normal_style
            ),
            Paragraph(
                appointment.appointment_time.strftime(
                    '%I:%M %p'
                ),
                normal_style
            ),
            Paragraph(
                '<b>Prescription Date</b>',
                normal_style
            ),
            Paragraph(
                prescription.created_at.strftime(
                    '%d %b %Y'
                ),
                normal_style
            ),
        ],
    ]

    patient_table = Table(
        patient_info,
        colWidths=[
            32 * mm,
            55 * mm,
            32 * mm,
            55 * mm
        ]
    )

    patient_table.setStyle(
        TableStyle([
            (
                'BACKGROUND',
                (0, 0),
                (-1, -1),
                colors.HexColor('#FAFBFD')
            ),
            (
                'BOX',
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor('#E5E9EF')
            ),
            (
                'INNERGRID',
                (0, 0),
                (-1, -1),
                0.3,
                colors.HexColor('#E5E9EF')
            ),
            (
                'VALIGN',
                (0, 0),
                (-1, -1),
                'MIDDLE'
            ),
            (
                'LEFTPADDING',
                (0, 0),
                (-1, -1),
                7
            ),
            (
                'RIGHTPADDING',
                (0, 0),
                (-1, -1),
                7
            ),
            (
                'TOPPADDING',
                (0, 0),
                (-1, -1),
                7
            ),
            (
                'BOTTOMPADDING',
                (0, 0),
                (-1, -1),
                7
            ),
        ])
    )

    story.append(patient_table)

    # --------------------------------------------------------
    # DIAGNOSIS
    # --------------------------------------------------------

    story.append(
        Paragraph(
            'DIAGNOSIS',
            section_style
        )
    )

    diagnosis_text = (
        prescription.diagnosis
        if prescription.diagnosis
        else 'No diagnosis provided.'
    )

    diagnosis_table = Table(
        [
            [
                Paragraph(
                    diagnosis_text,
                    normal_style
                )
            ]
        ],
        colWidths=[174 * mm]
    )

    diagnosis_table.setStyle(
        TableStyle([
            (
                'BACKGROUND',
                (0, 0),
                (-1, -1),
                colors.HexColor('#FAFBFD')
            ),
            (
                'BOX',
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor('#E5E9EF')
            ),
            (
                'LEFTPADDING',
                (0, 0),
                (-1, -1),
                9
            ),
            (
                'RIGHTPADDING',
                (0, 0),
                (-1, -1),
                9
            ),
            (
                'TOPPADDING',
                (0, 0),
                (-1, -1),
                8
            ),
            (
                'BOTTOMPADDING',
                (0, 0),
                (-1, -1),
                8
            ),
        ])
    )

    story.append(diagnosis_table)

    # --------------------------------------------------------
    # MEDICINES
    # --------------------------------------------------------

    story.append(
        Paragraph(
            'PRESCRIBED MEDICINES',
            section_style
        )
    )

    medicine_data = [
        [
            Paragraph(
                '<b>Medicine</b>',
                normal_style
            ),
            Paragraph(
                '<b>Dosage</b>',
                normal_style
            ),
            Paragraph(
                '<b>Frequency</b>',
                normal_style
            ),
            Paragraph(
                '<b>Duration</b>',
                normal_style
            ),
            Paragraph(
                '<b>Instructions</b>',
                normal_style
            ),
        ]
    ]

    medicines = prescription.medicines.all()

    for medicine in medicines:

        medicine_data.append([
            Paragraph(
                medicine.medicine_name,
                medicine_style
            ),
            Paragraph(
                medicine.dosage or '—',
                normal_style
            ),
            Paragraph(
                medicine.frequency or '—',
                normal_style
            ),
            Paragraph(
                medicine.duration or '—',
                normal_style
            ),
            Paragraph(
                medicine.instructions or '—',
                normal_style
            ),
        ])

    if not medicines.exists():

        medicine_data.append([
            Paragraph(
                'No medicines were prescribed.',
                small_style
            ),
            '',
            '',
            '',
            '',
        ])

    medicine_table = Table(
        medicine_data,
        colWidths=[
            42 * mm,
            28 * mm,
            30 * mm,
            27 * mm,
            47 * mm,
        ],
        repeatRows=1
    )

    medicine_table.setStyle(
        TableStyle([
            (
                'BACKGROUND',
                (0, 0),
                (-1, 0),
                colors.HexColor('#F1F5F9')
            ),
            (
                'GRID',
                (0, 0),
                (-1, -1),
                0.4,
                colors.HexColor('#E5E9EF')
            ),
            (
                'VALIGN',
                (0, 0),
                (-1, -1),
                'TOP'
            ),
            (
                'LEFTPADDING',
                (0, 0),
                (-1, -1),
                6
            ),
            (
                'RIGHTPADDING',
                (0, 0),
                (-1, -1),
                6
            ),
            (
                'TOPPADDING',
                (0, 0),
                (-1, -1),
                7
            ),
            (
                'BOTTOMPADDING',
                (0, 0),
                (-1, -1),
                7
            ),
        ])
    )

    story.append(medicine_table)

    # --------------------------------------------------------
    # DOCTOR'S INSTRUCTIONS
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "DOCTOR'S INSTRUCTIONS",
            section_style
        )
    )

    notes_text = (
        prescription.notes
        if prescription.notes
        else 'No additional instructions provided.'
    )

    notes_table = Table(
        [
            [
                Paragraph(
                    notes_text,
                    normal_style
                )
            ]
        ],
        colWidths=[174 * mm]
    )

    notes_table.setStyle(
        TableStyle([
            (
                'BACKGROUND',
                (0, 0),
                (-1, -1),
                colors.HexColor('#FAFBFD')
            ),
            (
                'BOX',
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor('#E5E9EF')
            ),
            (
                'LEFTPADDING',
                (0, 0),
                (-1, -1),
                9
            ),
            (
                'RIGHTPADDING',
                (0, 0),
                (-1, -1),
                9
            ),
            (
                'TOPPADDING',
                (0, 0),
                (-1, -1),
                8
            ),
            (
                'BOTTOMPADDING',
                (0, 0),
                (-1, -1),
                8
            ),
        ])
    )

    story.append(notes_table)

    # --------------------------------------------------------
    # DOCTOR SIGNATURE
    # --------------------------------------------------------

    story.append(Spacer(1, 25))

    signature_data = [
        [
            '',
            Paragraph(
                f'<b>Dr. {doctor_name}</b><br/>'
                f'<font size="8" color="#6B7280">'
                f'{specialization}'
                f'</font>',
                normal_style
            )
        ]
    ]

    signature_table = Table(
        signature_data,
        colWidths=[
            105 * mm,
            69 * mm
        ]
    )

    signature_table.setStyle(
        TableStyle([
            (
                'LINEABOVE',
                (1, 0),
                (1, 0),
                0.6,
                colors.HexColor('#9CA3AF')
            ),
            (
                'ALIGN',
                (1, 0),
                (1, 0),
                'CENTER'
            ),
            (
                'VALIGN',
                (0, 0),
                (-1, -1),
                'TOP'
            ),
            (
                'TOPPADDING',
                (0, 0),
                (-1, -1),
                7
            ),
        ])
    )

    story.append(signature_table)

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------

    story.append(Spacer(1, 18))

    footer_table = Table(
        [[
            Paragraph(
                'CarePlus Hospital • Prescription Record',
                small_style
            ),
            Paragraph(
                f'Prescription #{prescription.id}',
                small_style
            ),
        ]],
        colWidths=[
            120 * mm,
            54 * mm
        ]
    )

    footer_table.setStyle(
        TableStyle([
            (
                'LINEABOVE',
                (0, 0),
                (-1, 0),
                0.5,
                colors.HexColor('#E5E9EF')
            ),
            (
                'TOPPADDING',
                (0, 0),
                (-1, -1),
                7
            ),
            (
                'ALIGN',
                (1, 0),
                (1, 0),
                'RIGHT'
            ),
        ])
    )

    story.append(footer_table)

    # --------------------------------------------------------
    # BUILD PDF
    # --------------------------------------------------------

    document.build(story)

    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/pdf'
    )

    response['Content-Disposition'] = (
        f'attachment; '
        f'filename="CarePlus_Prescription_{prescription.id}.pdf"'
    )

    return response

# ============================================================
# PUBLIC DOCTORS DIRECTORY
# ============================================================

def doctors_directory(request):

    doctors = (
        Doctor.objects
        .filter(is_available=True)
        .select_related('user')
        .order_by('user__first_name', 'user__last_name')
    )

    # --------------------------------------------------------
    # SEARCH BY DOCTOR NAME
    # --------------------------------------------------------

    search = request.GET.get(
        'search',
        ''
    ).strip()

    if search:

        doctors = doctors.filter(
            user__first_name__icontains=search
        ) | doctors.filter(
            user__last_name__icontains=search
        ) | doctors.filter(
            user__username__icontains=search
        )

    # --------------------------------------------------------
    # FILTER BY SPECIALIZATION
    # --------------------------------------------------------

    specialization = request.GET.get(
        'specialization',
        ''
    ).strip()

    if specialization:

        doctors = doctors.filter(
            specialization=specialization
        )

    # --------------------------------------------------------
    # FILTER BY EXPERIENCE
    # --------------------------------------------------------

    experience = request.GET.get(
        'experience',
        ''
    ).strip()

    if experience:

        try:
            experience_value = int(experience)

            doctors = doctors.filter(
                experience__gte=experience_value
            )

        except ValueError:
            pass

    # --------------------------------------------------------
    # FILTER BY AVAILABILITY
    # --------------------------------------------------------

    availability = request.GET.get(
        'availability',
        ''
    ).strip()

    if availability == 'available':

        doctors = doctors.filter(
            is_available=True
        )

    # --------------------------------------------------------
    # SPECIALIZATION LIST
    # --------------------------------------------------------

    specializations = Doctor.SPECIALIZATION_CHOICES

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render(
        request,
        'doctors.html',
        {
            'doctors': doctors,
            'specializations': specializations,
            'search': search,
            'selected_specialization': specialization,
            'selected_experience': experience,
            'selected_availability': availability,
        }
    )