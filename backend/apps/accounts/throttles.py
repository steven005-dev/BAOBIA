from rest_framework.throttling import SimpleRateThrottle


class LoginIPThrottle(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        return f"auth-login-ip:{self.get_ident(request)}"


class LoginPhoneThrottle(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        phone = str(request.data.get("phone", "")).strip().lower()
        return f"auth-login-phone:{phone}"


class LoginAttemptThrottle:
    """Apply both independent limits to each login attempt."""

    def __init__(self):
        self.throttles = (LoginIPThrottle(), LoginPhoneThrottle())

    def allow_request(self, request, view):
        allowed = True
        for throttle in self.throttles:
            allowed = throttle.allow_request(request, view) and allowed
        return allowed

    def wait(self):
        waits = [throttle.wait() for throttle in self.throttles if throttle.wait() is not None]
        return max(waits) if waits else None
