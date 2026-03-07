from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from .models import User
from django.core.files.storage import default_storage
from .otp_utils import generate_otp, send_otp_sms, is_otp_valid


def redirect_by_role(user):
    if user.role == 'recruiter':
        return redirect('recruiter_dashboard')
    return redirect('seeker_dashboard')


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
                u = User.objects.get(phone=identifier)
                user = authenticate(request, username=u.phone, password=password)
            except User.DoesNotExist:
                pass

        # Try username
        if user is None and not identifier.isdigit():
            try:
                u = User.objects.get(username=identifier)
                user = authenticate(request, username=u.phone, password=password)
            except User.DoesNotExist:
                pass

        # Try email
        if user is None and '@' in identifier:
            try:
                u = User.objects.get(email=identifier)
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


def signup_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)
    return render(request, 'users/signup.html')


def send_otp_view(request):
    if request.method != 'POST':
        return redirect('signup')

    phone  = request.POST.get('phone', '').strip()
    intent = request.POST.get('intent', 'seeker')

    if not phone or len(phone) != 10 or not phone.isdigit():
        messages.error(request, 'Enter a valid 10-digit mobile number.')
        return render(request, 'users/signup.html', {'phone': phone, 'intent': intent})

    # Get or create user — allow re-signup if no password set yet
    user, created = User.objects.get_or_create(phone=phone)

    # If user already has a password they are registered — send to login
    if not created and user.has_usable_password():
        messages.error(request, 'This number is already registered. Please login.')
        return redirect('login')

    otp = generate_otp()
    user.otp            = otp
    user.otp_created_at = timezone.now()
    user.save()

    send_otp_sms(phone, otp)

    return render(request, 'users/signup.html', {
        'otp_sent': True,
        'phone':    phone,
        'intent':   intent,
    })


def verify_otp_view(request):
    if request.method != 'POST':
        return redirect('signup')

    phone  = request.POST.get('phone', '').strip()
    otp    = request.POST.get('otp', '').strip()
    intent = request.POST.get('intent', 'seeker')

    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        messages.error(request, 'Phone not found. Please try again.')
        return redirect('signup')

    valid, message = is_otp_valid(user, otp)

    if not valid:
        messages.error(request, message)
        return render(request, 'users/signup.html', {
            'otp_sent': True,
            'phone':    phone,
            'intent':   intent,
        })

    user.otp            = None
    user.otp_created_at = None
    user.save()

    login(request, user)
    request.session['intent'] = intent
    return redirect('complete_profile')


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

        # Check username uniqueness
        if username:
            if User.objects.filter(username=username).exclude(pk=user.pk).exists():
                messages.error(request, 'Username already taken. Choose another.')
                return render(request, 'users/complete_profile.html', {
                    'intent': request.session.get('intent', 'seeker')
                })
            user.username = username

        if email:
            user.email = email

        password  = request.POST.get('password', '').strip()
        password2 = request.POST.get('password2', '').strip()

        if not password or len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
            return render(request, 'users/complete_profile.html', {
                'intent': request.session.get('intent', 'seeker')
            })

        if password != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'users/complete_profile.html', {
                'intent': request.session.get('intent', 'seeker')
            })

        user.set_password(password)
        user.save()
        login(request, user)
        messages.success(request, f'Welcome to KaamMilao, {user.full_name}! 🎉')
        return redirect_by_role(user)

    intent = request.session.get('intent', 'seeker')
    return render(request, 'users/complete_profile.html', {'intent': intent})


def logout_view(request):
    logout(request)
    messages.info(request, 'Logged out successfully.')
    return redirect('login')


@login_required
def notifications_view(request):
    from .models import Notification
    notifs = Notification.objects.filter(recipient=request.user)
    notifs.filter(is_read=False).update(is_read=True)
    return render(request, 'users/notifications.html', {'notifications': notifs})


@login_required
def my_profile_view(request):
    from applications.models import Application
    from jobs.models import Job
    from .models import Rating

    profile_user = request.user
    ratings      = Rating.objects.filter(rated=profile_user).select_related('rater')

    if profile_user.role == 'seeker':
        applications = Application.objects.filter(applicant=profile_user).select_related('job').order_by('-applied_at')
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
    from django.shortcuts import get_object_or_404

    profile_user = get_object_or_404(User, id=user_id)
    ratings      = Rating.objects.filter(rated=profile_user).select_related('rater')

    if profile_user.role == 'seeker':
        applications = Application.objects.filter(applicant=profile_user).select_related('job').order_by('-applied_at')
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

        # Profile photo
        if 'photo' in request.FILES:
            user.photo = request.FILES['photo']

        # Change password
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
        rated = get_object_or_404(User, id=user_id)
        stars  = int(request.POST.get('stars', 5))
        review = request.POST.get('review', '').strip()
        Rating.objects.update_or_create(
            rater=request.user, rated=rated,
            defaults={'stars': stars, 'review': review}
        )
        messages.success(request, f'Rated {rated.full_name} {stars}★')
    return redirect('view_profile', user_id=user_id)
