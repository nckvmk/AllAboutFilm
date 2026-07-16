"""Custom middleware for the home app."""

from django.contrib.auth import logout


class SuspendedUserMiddleware:
    """Immediately logs out a user whose account has been suspended
    (is_active = False), so a suspension takes effect even mid-session."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_active:
            logout(request)
        return self.get_response(request)
