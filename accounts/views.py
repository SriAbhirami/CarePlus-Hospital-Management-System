from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.utils.http import url_has_allowed_host_and_scheme

from patients.models import Patient

from .forms import RegisterForm, LoginForm


# ============================================================
# HOME
# ============================================================

def home_view(request):
    return render(
        request,
        'home.html'
    )


# ============================================================
# REGISTER
# ============================================================

def register_view(request):

    if request.method == 'POST':

        form = RegisterForm(request.POST)

        if form.is_valid():

            # Create the user
            user = form.save()

            # Create the patient profile
            Patient.objects.create(
                user=user,
                date_of_birth=form.cleaned_data['date_of_birth'],
                blood_group=form.cleaned_data['blood_group'],
                allergies=form.cleaned_data['allergies'],
                address=form.cleaned_data['address']
            )

            # Log the patient in
            login(request, user)

            return redirect('patient_dashboard')

    else:

        form = RegisterForm()

    return render(
        request,
        'accounts/register.html',
        {
            'form': form
        }
    )


# ============================================================
# LOGIN
# ============================================================

def login_view(request):

    # --------------------------------------------------------
    # Preserve the destination the user originally requested
    # --------------------------------------------------------

    next_url = (
        request.POST.get('next')
        or request.GET.get('next')
        or ''
    )

    if request.method == 'POST':

        form = LoginForm(request.POST)

        if form.is_valid():

            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(
                request,
                username=username,
                password=password
            )

            if user is not None:

                login(request, user)

                # ------------------------------------------------
                # Return the user to the requested page
                # ------------------------------------------------
                #
                # Example:
                # /book-appointment/?doctor=12
                #
                # This preserves the exact doctor selected
                # before login.
                # ------------------------------------------------

                if next_url and url_has_allowed_host_and_scheme(
                    url=next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure()
                ):
                    return redirect(next_url)

                # ------------------------------------------------
                # Normal role-based login flow
                # ------------------------------------------------

                if user.role == 'PATIENT':
                    return redirect('patient_dashboard')

                elif user.role == 'DOCTOR':
                    return redirect('doctor_dashboard')

                elif user.role == 'STAFF':
                    # Keep STAFF role active.
                    # Staff dashboard can be connected later.
                    return redirect('home')

                elif user.role == 'ADMIN':
                    return redirect('admin_panel:dashboard')

            else:

                form.add_error(
                    None,
                    'Invalid username or password.'
                )

    else:

        form = LoginForm()

    return render(
        request,
        'accounts/login.html',
        {
            'form': form,
            'next': next_url
        }
    )


# ============================================================
# LOGOUT
# ============================================================

def logout_view(request):

    logout(request)

    return redirect('home')


# ============================================================
# ABOUT
# ============================================================

def about(request):
    return render(
        request,
        'about.html'
    )