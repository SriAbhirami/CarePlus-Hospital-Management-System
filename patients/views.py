from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from doctors.models import Doctor
from patients.models import Patient

from appointments.models import (
    Appointment,
    PaymentTransaction,
    Prescription,
)

from io import BytesIO

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
# PATIENT DASHBOARD
# ============================================================

def patient_dashboard(request):

    patient = request.user.patient_profile

    # --------------------------------------------------------
    # HANDLE PROFILE PHOTO UPLOAD
    # --------------------------------------------------------

    if request.method == 'POST':

        if request.FILES.get('profile_pic'):

            patient.profile_pic = request.FILES['profile_pic']

            patient.save()

        return redirect('patient_dashboard')

    # --------------------------------------------------------
    # GET APPOINTMENTS
    # --------------------------------------------------------

    appointments = Appointment.objects.filter(
        patient=patient
    ).order_by(
        'appointment_date',
        'appointment_time'
    )

    return render(
        request,
        'patient/dashboard.html',
        {
            'patient': patient,
            'appointments': appointments
        }
    )


# ============================================================
# PATIENT BILLS
# ============================================================

def patient_bills(request):

    patient = request.user.patient_profile

    transactions = PaymentTransaction.objects.filter(
        patient=patient
    ).select_related(
        'doctor__user',
        'appointment'
    ).order_by(
        '-created_at'
    )

    successful_count = transactions.filter(
        status='SUCCESS'
    ).count()

    declined_count = transactions.filter(
        status='DECLINED'
    ).count()

    return render(
        request,
        'patient/bills.html',
        {
            'patient': patient,
            'transactions': transactions,
            'successful_count': successful_count,
            'declined_count': declined_count,
        }
    )


# ============================================================
# PATIENT PRESCRIPTIONS
# ============================================================

def patient_prescriptions(request):

    patient = request.user.patient_profile

    prescriptions = (
        Prescription.objects
        .filter(
            appointment__patient=patient
        )
        .select_related(
            'appointment__doctor__user',
            'appointment__patient__user'
        )
        .prefetch_related(
            'medicines'
        )
        .order_by(
            '-created_at'
        )
    )

    return render(
        request,
        'patient/prescriptions.html',
        {
            'patient': patient,
            'prescriptions': prescriptions,
        }
    )


# ============================================================
# PATIENT PRESCRIPTION DETAIL
# ============================================================

def patient_prescription_detail(
    request,
    prescription_id
):

    patient = request.user.patient_profile

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
        appointment__patient=patient
    )

    return render(
        request,
        'patient/prescription_detail.html',
        {
            'patient': patient,
            'prescription': prescription,
        }
    )


# ============================================================
# PATIENT DOWNLOAD PRESCRIPTION PDF
# ============================================================

def patient_download_prescription_pdf(
    request,
    prescription_id
):

    patient = request.user.patient_profile

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
        appointment__patient=patient
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
        'PatientHospitalStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#132238'),
        alignment=TA_CENTER,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        'PatientSubtitleStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#6B7280'),
        alignment=TA_CENTER,
        spaceAfter=12,
    )

    title_style = ParagraphStyle(
        'PatientTitleStyle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1769AA'),
        alignment=TA_LEFT,
        spaceAfter=10,
    )

    section_style = ParagraphStyle(
        'PatientSectionStyle',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#172033'),
        spaceBefore=8,
        spaceAfter=7,
    )

    normal_style = ParagraphStyle(
        'PatientNormalStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#374151'),
    )

    small_style = ParagraphStyle(
        'PatientSmallStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#6B7280'),
    )

    medicine_style = ParagraphStyle(
        'PatientMedicineStyle',
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

    # Hospital header
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

    # Header divider
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

    # Prescription title
    story.append(
        Paragraph(
            'MEDICAL PRESCRIPTION',
            title_style
        )
    )

    prescription_number = f'RX-{prescription.id:05d}'

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
    # PATIENT AND APPOINTMENT INFORMATION
    # --------------------------------------------------------

    story.append(
        Paragraph(
            'PATIENT & APPOINTMENT INFORMATION',
            section_style
        )
    )

    appointment = prescription.appointment
    patient_user = appointment.patient.user

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
            Paragraph('<b>Patient</b>', normal_style),
            Paragraph(patient_name, normal_style),
            Paragraph('<b>Doctor</b>', normal_style),
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
                'CarePlus Hospital • Patient Prescription Record',
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
# SPECIALIZATION DETAIL
# ============================================================

def specialization_detail(request, specialization):
    """
    Display details for a medical specialization
    and show available doctors belonging to that specialty.
    """

    specialization_data = {
    'CARDIOLOGY': {
        'title': 'Cardiology',
        'description': 'Comprehensive care for heart and cardiovascular conditions, with expert diagnosis, treatment, and preventive care.',
        'image': '/static/images/specializations/cardiology.jpg',
    },

    'DERMATOLOGY': {
        'title': 'Dermatology',
        'description': 'Expert diagnosis and treatment for skin, hair, and nail conditions, with personalized dermatological care.',
        'image': '/static/images/specializations/dermatology1.jpg',
    },

    'PEDIATRICS': {
        'title': 'Pediatrics',
        'description': 'Specialized healthcare for infants, children, and adolescents, supporting healthy growth and development.',
        'image': '/static/images/specializations/pediatrics.jpg',
    },

    'NEUROLOGY': {
        'title': 'Neurology',
        'description': 'Specialized care for conditions affecting the brain, spinal cord, nerves, and overall nervous system.',
        'image': '/static/images/specializations/neurology.jpg',
    },

    'ORTHOPEDICS': {
        'title': 'Orthopedics',
        'description': 'Comprehensive treatment for bones, joints, muscles, ligaments, and other musculoskeletal conditions.',
        'image': '/static/images/specializations/orthopedics.jpg',
    },

    'GYNECOLOGY': {
        'title': 'Gynecology',
        'description': 'Dedicated healthcare for women, covering reproductive health, wellness, diagnosis, and treatment.',
        'image': '/static/images/specializations/gynecology1.jpg',
    },

    'GENERAL_MEDICINE': {
        'title': 'General Medicine',
        'description': 'Primary healthcare for common illnesses, preventive care, routine consultations, and overall wellness.',
        'image': '/static/images/specializations/general medicine.jpg',
    },

    'ENT': {
        'title': 'ENT',
        'description': 'Specialized diagnosis and treatment of conditions affecting the ear, nose, throat, and related structures.',
        'image': '/static/images/specializations/ent.jpg',
    },

    'OPHTHALMOLOGY': {
        'title': 'Ophthalmology',
        'description': 'Comprehensive eye care including vision assessment, diagnosis, treatment, and management of eye conditions.',
        'image': '/static/images/specializations/eye.jpg',
    },

    'DENTISTRY': {
        'title': 'Dentistry',
        'description': 'Complete dental care focused on oral health, prevention, diagnosis, and treatment of dental conditions.',
        'image': '/static/images/specializations/dentistry.jpg',
    },
}

    specialty = specialization.upper()

    data = specialization_data.get(
        specialty
    )

    if not data:
        return redirect('home')

    doctors = Doctor.objects.filter(
        specialization=specialty,
        is_available=True
    ).select_related(
        'user'
    )

    context = {
        'specialization': data,
        'doctors': doctors,
    }

    return render(
        request,
        'specialization_detail.html',
        context
    )
