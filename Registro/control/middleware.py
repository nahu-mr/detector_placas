from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import resolve_url


class LoginRequiredMiddleware:
    """Require authentication for the app unless the route is explicitly public."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated or self._is_public_path(request.path_info):
            return self.get_response(request)

        return redirect_to_login(request.get_full_path(), resolve_url(settings.LOGIN_URL))

    def _is_public_path(self, path):
        login_path = resolve_url(settings.LOGIN_URL)
        logout_path = resolve_url(getattr(settings, 'LOGOUT_REDIRECT_URL', login_path))
        static_url = getattr(settings, 'STATIC_URL', '/static/')

        return (
            path == login_path
            or path.startswith(f'{login_path}?')
            or path == '/logout/'
            or path == logout_path
            or path.startswith('/admin/')
            or path.startswith(static_url)
        )
