from django.db import models
from django.conf import settings


class Doctor(models.Model):

    SPECIALIZATION_CHOICES = (
        ('CARDIOLOGY', 'Cardiology'),
        ('DERMATOLOGY', 'Dermatology'),
        ('PEDIATRICS', 'Pediatrics'),
        ('NEUROLOGY', 'Neurology'),
        ('ORTHOPEDICS', 'Orthopedics'),
        ('GYNECOLOGY', 'Gynecology'),
        ('GENERAL_MEDICINE', 'General Medicine'),
        ('ENT', 'ENT'),
        ('OPHTHALMOLOGY', 'Ophthalmology'),
        ('DENTISTRY', 'Dentistry'),
    )

    DAYS_CHOICES = (
        ('MON', 'Monday'),
        ('TUE', 'Tuesday'),
        ('WED', 'Wednesday'),
        ('THU', 'Thursday'),
        ('FRI', 'Friday'),
        ('SAT', 'Saturday'),
        ('SUN', 'Sunday'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='doctor_profile'
    )

    specialization = models.CharField(
        max_length=50,
        choices=SPECIALIZATION_CHOICES
    )

    qualification = models.CharField(
        max_length=200
    )

    experience = models.PositiveIntegerField(
        help_text='Experience in years'
    )

    consultation_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    available_days = models.CharField(
        max_length=100
    )

    available_time_start = models.TimeField()

    available_time_end = models.TimeField()

    profile_pic = models.ImageField(
        upload_to='doctors/',
        blank=True,
        null=True
    )

    rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=0.0
    )

    is_available = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.username}"