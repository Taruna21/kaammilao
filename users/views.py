from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from .models import User, Notification
from .otp_utils import (
    generate_otp, send_otp_sms, send_otp_email,
    send_password_reset_email, is_otp_valid
)


def redirect_by_role(user):
    if user.role == 'recruiter':
        return redirect('recruiter_dashboard')
    return redirect('seeker_dashboard')


# ── LOGIN ─────────────────────────────────────────────────
def login_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)

    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        password   = request.POST.get('password', '').strip()

        if not identifier or not password:
            messages.error(request, 'Please enter your login ID and password.')
            return render(request, 'users/login.html', {'identifier': identifier})

        user = None

        # Try phone
        if identifier.isdigit():
            try:
                u    = User.objects.get(phone=identifier)
                user = authenticate(request, username=u.phone, password=password)
            except User.DoesNotExist:
                pass

        # Try username
        if user is None and not identifier.isdigit() and '@' not in identifier:
            try:
                u    = User.objects.get(username=identifier)
                user = authenticate(request, username=u.phone, password=password)
            except User.DoesNotExist:
                pass

        # Try email
        if user is None and '@' in identifier:
            try:
                u    = User.objects.get(email=identifier)
                user = authenticate(request, username=u.phone, password=password)
            except User.DoesNotExist:
                pass

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.full_name or user.phone}!')
            return redirect_by_role(user)
        else:
            messages.error(request, 'Invalid credentials. Please try again.')
            return render(request, 'users/login.html', {'identifier': identifier})

    return render(request, 'users/login.html')


# ── SIGNUP ────────────────────────────────────────────────
def signup_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)
    return render(request, 'users/signup.html')


def send_otp_view(request):
    if request.method != 'POST':
        return redirect('signup')

    method = request.POST.get('method', 'phone')  # 'phone' or 'email'
    intent = request.POST.get('intent', 'seeker')

    if method == 'email':
        email = request.POST.get('email', '').strip().lower()

        if not email or '@' not in email:
            messages.error(request, 'Enter a valid email address.')
            return render(request, 'users/signup.html', {'method': method, 'intent': intent})

        # Check already registered with usable password
        existing = User.objects.filter(email=email).first()
        if existing and existing.has_usable_password():
            messages.error(request, 'This email is already registered. Please login.')
            return redirect('login')

        # Get or create by email — use email as temp phone
        user, _ = User.objects.get_or_create(email=email, defaults={'phone': f'e_{email[:10]}'})
        otp = generate_otp()
        user.otp            = otp
        user.otp_created_at = timezone.now()
        user.save()

        success = send_otp_email(email, otp)
        if not success:
            messages.error(request, 'Failed to send OTP email. Please try again.')
            return render(request, 'users/signup.html', {'method': method, 'intent': intent})

        return render(request, 'users/signup.html', {
            'otp_sent': True,
            'method':   'email',
            'contact':  email,
            'intent':   intent,
        })

    else:
        # Phone method
        phone = request.POST.get('phone', '').strip()

        if not phone or len(phone) != 10 or not phone.isdigit():
            messages.error(request, 'Enter a valid 10-digit mobile number.')
            return render(request, 'users/signup.html', {'method': method, 'intent': intent})

        existing = User.objects.filter(phone=phone).first()
        if existing and existing.has_usable_password():
            messages.error(request, 'This number is already registered. Please login.')
            return redirect('login')

        user, _ = User.objects.get_or_create(phone=phone)
        otp = generate_otp()
        user.otp            = otp
        user.otp_created_at = timezone.now()
        user.save()

        success = send_otp_sms(phone, otp)
        if not success:
            messages.error(request, 'Failed to send OTP. Please try again.')
            return render(request, 'users/signup.html', {'method': method, 'intent': intent})

        return render(request, 'users/signup.html', {
            'otp_sent': True,
            'method':   'phone',
            'contact':  phone,
            'intent':   intent,
        })


def verify_otp_view(request):
    if request.method != 'POST':
        return redirect('signup')

    method  = request.POST.get('method', 'phone')
    contact = request.POST.get('contact', '').strip()
    otp     = request.POST.get('otp', '').strip()
    intent  = request.POST.get('intent', 'seeker')

    try:
        if method == 'email':
            user = User.objects.get(email=contact)
        else:
            user = User.objects.get(phone=contact)
    except User.DoesNotExist:
        messages.error(request, 'Not found. Please try again.')
        return redirect('signup')

    valid, message = is_otp_valid(user, otp)
    if not valid:
        messages.error(request, message)
        return render(request, 'users/signup.html', {
            'otp_sent': True,
            'method':   method,
            'contact':  contact,
            'intent':   intent,
        })

    user.otp            = None
    user.otp_created_at = None
    user.save()

    login(request, user)
    request.session['intent'] = intent
    return redirect('complete_profile')


# ── COMPLETE PROFILE ──────────────────────────────────────
@login_required
def complete_profile_view(request):
    if request.method == 'POST':
        user           = request.user
        user.full_name = request.POST.get('full_name', '').strip()
        user.role      = request.POST.get('role', 'seeker')
        user.city      = request.POST.get('city', '').strip()
        user.address   = request.POST.get('address', '').strip()

        username = request.POST.get('username', '').strip()
        email    = request.POST.get('email', '').strip()
        phone    = request.POST.get('phone', '').strip()

        if username:
            if User.objects.filter(username=username).exclude(pk=user.pk).exists():
                messages.error(request, 'Username already taken.')
                return render(request, 'users/complete_profile.html', {
                    'intent': request.session.get('intent', 'seeker'), 'user': user
                })
            user.username = username

        if email and not user.email:
            user.email = email

        if phone and user.phone.startswith('e_'):
            # User signed up with email, now adding phone
            if User.objects.filter(phone=phone).exclude(pk=user.pk).exists():
                messages.error(request, 'This phone is already registered.')
                return render(request, 'users/complete_profile.html', {
                    'intent': request.session.get('intent', 'seeker'), 'user': user
                })
            user.phone = phone

        password  = request.POST.get('password', '').strip()
        password2 = request.POST.get('password2', '').strip()

        if not password or len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
            return render(request, 'users/complete_profile.html', {
                'intent': request.session.get('intent', 'seeker'), 'user': user
            })

        if password != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'users/complete_profile.html', {
                'intent': request.session.get('intent', 'seeker'), 'user': user
            })

        user.set_password(password)
        user.save()
        login(request, user)
        messages.success(request, f'Welcome to LocalServe, {user.full_name}! 🎉')
        if user.email:
            from .otp_utils import send_welcome_email
            send_welcome_email(user.email, user.full_name)
        return redirect_by_role(user)

    intent = request.session.get('intent', 'seeker')
    return render(request, 'users/complete_profile.html', {
        'intent': intent,
        'user':   request.user,
    })


# ── FORGOT PASSWORD ───────────────────────────────────────
def forgot_password_view(request):
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()

        user = None
        method = 'email'

        if '@' in identifier:
            user = User.objects.filter(email=identifier).first()
            method = 'email'
        elif identifier.isdigit():
            user = User.objects.filter(phone=identifier).first()
            method = 'phone'
        else:
            user = User.objects.filter(username=identifier).first()
            method = 'email' if user and user.email else 'phone'

        if not user:
            messages.error(request, 'No account found with that details.')
            return render(request, 'users/forgot_password.html')

        otp = generate_otp()
        user.otp            = otp
        user.otp_created_at = timezone.now()
        user.save()

        if method == 'email' and user.email:
            send_password_reset_email(user.email, otp)
            contact = user.email
        else:
            send_otp_sms(user.phone, otp)
            contact = user.phone

        return render(request, 'users/forgot_password.html', {
            'otp_sent': True,
            'contact':  contact,
            'method':   method,
            'user_id':  user.id,
        })

    return render(request, 'users/forgot_password.html')


def verify_reset_otp_view(request):
    if request.method != 'POST':
        return redirect('forgot_password')

    user_id = request.POST.get('user_id')
    otp     = request.POST.get('otp', '').strip()

    user = get_object_or_404(User, id=user_id)
    valid, message = is_otp_valid(user, otp)

    if not valid:
        messages.error(request, message)
        return render(request, 'users/forgot_password.html', {
            'otp_sent': True,
            'user_id':  user_id,
        })

    # OTP valid — store in session for reset
    request.session['reset_user_id'] = user.id
    user.otp = None
    user.otp_created_at = None
    user.save()

    return redirect('reset_password')


def reset_password_view(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(request, 'Session expired. Please try again.')
        return redirect('forgot_password')

    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        password  = request.POST.get('password', '').strip()
        password2 = request.POST.get('password2', '').strip()

        if not password or len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
            return render(request, 'users/reset_password.html')

        if password != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'users/reset_password.html')

        user.set_password(password)
        user.save()
        del request.session['reset_user_id']
        login(request, user)
        messages.success(request, 'Password reset successfully! Welcome back.')
        if user.email:
            from .otp_utils import send_password_reset_success_email
            send_password_reset_success_email(user.email, user.full_name or "User")
        return redirect_by_role(user)

    return render(request, 'users/reset_password.html')


# ── LOGOUT ────────────────────────────────────────────────
def logout_view(request):
    logout(request)
    messages.info(request, 'Logged out successfully.')
    return redirect('login')


# ── NOTIFICATIONS ─────────────────────────────────────────
@login_required
def notifications_view(request):
    notifs = Notification.objects.filter(recipient=request.user)
    notifs.filter(is_read=False).update(is_read=True)
    return render(request, 'users/notifications.html', {'notifications': notifs})


# ── PROFILES ──────────────────────────────────────────────
@login_required
def my_profile_view(request):
    from applications.models import Application
    from jobs.models import Job
    from .models import Rating

    profile_user = request.user
    ratings      = Rating.objects.filter(rated=profile_user).select_related('rater')

    if profile_user.role == 'seeker':
        applications = Application.objects.filter(
            applicant=profile_user).select_related('job').order_by('-applied_at')
        return render(request, 'users/profile.html', {
            'profile_user':      profile_user,
            'applications':      applications,
            'hired_count':       applications.filter(status='hired').count(),
            'shortlisted_count': applications.filter(status='shortlisted').count(),
            'ratings':           ratings,
            'avg_rating':        profile_user.avg_rating(),
            'rating_count':      ratings.count(),
            'is_own':            True,
        })
    else:
        jobs = Job.objects.filter(posted_by=profile_user).order_by('-created_at')
        return render(request, 'users/profile.html', {
            'profile_user': profile_user,
            'jobs':         jobs,
            'open_count':   jobs.filter(status='open').count(),
            'ratings':      ratings,
            'avg_rating':   profile_user.avg_rating(),
            'rating_count': ratings.count(),
            'is_own':       True,
        })


@login_required
def view_profile(request, user_id):
    from applications.models import Application
    from jobs.models import Job
    from .models import Rating

    profile_user = get_object_or_404(User, id=user_id)
    ratings      = Rating.objects.filter(rated=profile_user).select_related('rater')

    if profile_user.role == 'seeker':
        applications = Application.objects.filter(
            applicant=profile_user).select_related('job').order_by('-applied_at')
        return render(request, 'users/profile.html', {
            'profile_user':      profile_user,
            'applications':      applications,
            'hired_count':       applications.filter(status='hired').count(),
            'shortlisted_count': applications.filter(status='shortlisted').count(),
            'ratings':           ratings,
            'avg_rating':        profile_user.avg_rating(),
            'rating_count':      ratings.count(),
            'is_own':            request.user == profile_user,
        })
    else:
        jobs = Job.objects.filter(posted_by=profile_user).order_by('-created_at')
        return render(request, 'users/profile.html', {
            'profile_user': profile_user,
            'jobs':         jobs,
            'open_count':   jobs.filter(status='open').count(),
            'ratings':      ratings,
            'avg_rating':   profile_user.avg_rating(),
            'rating_count': ratings.count(),
            'is_own':       request.user == profile_user,
        })


@login_required
def edit_profile_view(request):
    if request.method == 'POST':
        user           = request.user
        user.full_name = request.POST.get('full_name', '').strip()
        user.city      = request.POST.get('city', '').strip()
        user.address   = request.POST.get('address', '').strip()
        user.bio       = request.POST.get('bio', '').strip()
        user.skills    = request.POST.get('skills', '').strip()

        if user.role == 'seeker':
            user.is_available = request.POST.get('is_available') == 'on'

        email    = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()

        if username and User.objects.filter(username=username).exclude(pk=user.pk).exists():
            messages.error(request, 'Username already taken.')
            return render(request, 'users/edit_profile.html', {'user': user})

        if email:    user.email    = email
        if username: user.username = username

        if 'photo' in request.FILES:
            user.photo = request.FILES['photo']

        new_password  = request.POST.get('new_password', '').strip()
        new_password2 = request.POST.get('new_password2', '').strip()
        if new_password:
            if len(new_password) < 6:
                messages.error(request, 'Password must be at least 6 characters.')
                return render(request, 'users/edit_profile.html', {'user': user})
            if new_password != new_password2:
                messages.error(request, 'Passwords do not match.')
                return render(request, 'users/edit_profile.html', {'user': user})
            user.set_password(new_password)
            login(request, user)

        user.save()
        messages.success(request, 'Profile updated!')
        return redirect('my_profile')

    return render(request, 'users/edit_profile.html', {'user': request.user})


@login_required
def rate_user(request, user_id):
    from .models import Rating
    if request.method == 'POST':
        rated  = get_object_or_404(User, id=user_id)
        stars  = int(request.POST.get('stars', 5))
        review = request.POST.get('review', '').strip()
        Rating.objects.update_or_create(
            rater=request.user, rated=rated,
            defaults={'stars': stars, 'review': review}
        )
        messages.success(request, f'Rated {rated.full_name} {stars}★')
    return redirect('view_profile', user_id=user_id)
