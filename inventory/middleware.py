import re
from django.shortcuts import redirect
from django.conf import settings
from urllib.parse import quote


class LoginRequiredMiddleware:
    """
    Redirect unauthenticated requests to the login page.

    Exempt paths:
    - Login / logout URLs
    - Django admin (has its own login)
    - Static and media files (served by WhiteNoise / django.views.static)
    - Print-worker API endpoints that use Bearer token auth
    """

    EXEMPT_PREFIXES = (
        '/accounts/login/',
        '/accounts/logout/',
        '/fra-panel/',
        '/static/',
        '/media/',
    )

    # Print-worker endpoints that use Bearer token auth (not session auth)
    _PRINT_WORKER_RE = re.compile(
        r'^/api/print-jobs/(?:pending/|\d+/(?:update-status|label\.png|status)/)$'
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            path = request.path
            is_exempt = any(path.startswith(p) for p in self.EXEMPT_PREFIXES)
            if not is_exempt and not self._PRINT_WORKER_RE.match(path):
                login_url = settings.LOGIN_URL
                next_url = request.get_full_path()
                return redirect(f'{login_url}?next={quote(next_url)}')

        return self.get_response(request)
