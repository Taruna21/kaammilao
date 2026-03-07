from django.urls import path
from . import views

urlpatterns = [
    path('login/',                         views.login_view,             name='login'),
    path('signup/',                        views.signup_view,            name='signup'),
    path('send-otp/',                      views.send_otp_view,          name='send_otp'),
    path('verify-otp/',                    views.verify_otp_view,        name='verify_otp'),
    path('complete-profile/',              views.complete_profile_view,  name='complete_profile'),
    path('logout/',                        views.logout_view,            name='logout'),
    path('notifications/',                 views.notifications_view,     name='notifications'),
    path('profile/',                       views.my_profile_view,        name='my_profile'),
    path('profile/edit/',                  views.edit_profile_view,      name='edit_profile'),
    path('profile/<int:user_id>/',         views.view_profile,           name='view_profile'),
    path('profile/<int:user_id>/rate/',    views.rate_user,              name='rate_user'),
    path('forgot-password/',               views.forgot_password_view,   name='forgot_password'),
    path('verify-reset-otp/',              views.verify_reset_otp_view,  name='verify_reset_otp'),
    path('reset-password/',                views.reset_password_view,    name='reset_password'),
]
