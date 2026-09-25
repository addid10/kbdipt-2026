from django.urls import path

from . import views


urlpatterns = [
    path("login/", views.user_login, name="user.login"),
    path("register/", views.user_register, name="user.register"),
    path("logout/", views.user_logout, name="user.logout"),
    path("profile/", views.profile, name="user.profile"),
    path("", views.home, name="public.home"),
    path("locations/<slug:code>/", views.site_detail, name="public.site_detail"),
    path("alerts/", views.alerts, name="public.alerts"),
    path("history/", views.history, name="public.history"),
    path("info/", views.info, name="public.info"),
    # Operator access intentionally has no link in the user-facing interface.
    # Staff can open this route directly when needed.
    path("management/login/", views.management_login, name="management.login"),
    path("management/logout/", views.management_logout, name="management.logout"),
]
