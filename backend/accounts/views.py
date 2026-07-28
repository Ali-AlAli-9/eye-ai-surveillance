import logging
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.core.cache import cache
from django.conf import settings
from .forms import EyeAIAuthenticationForm

audit = logging.getLogger("audit")


def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    ip = _get_client_ip(request)
    form = EyeAIAuthenticationForm(request=request, data=request.POST or None)
    error = None

    lock_key = f"login_locked_{ip}"
    if cache.get(lock_key):
        error = "تم حظرك مؤقتاً — حاول بعد 15 دقيقة"
        return render(request, "accounts/login.html", {"form": form, "error": error})

    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]

        user_obj = authenticate(request, username=username, password=password)

        if user_obj is not None:
            cache.delete(f"login_attempts_{ip}")
            audit.warning(f"LOGIN_SUCCESS: {username} from {ip}")
            login(request, user_obj)
            return redirect("dashboard")
        else:
            attempts_key = f"login_attempts_{ip}"
            attempts = cache.get(attempts_key, 0) + 1
            if attempts >= settings.LOGIN_ATTEMPTS_LIMIT:
                cache.set(lock_key, True, settings.LOGIN_ATTEMPTS_TIMEOUT)
                cache.delete(attempts_key)
                audit.warning(f"LOGIN_LOCKED: {ip} after {attempts} attempts")
                error = "تم حظرك مؤقتاً — حاول بعد 15 دقيقة"
            else:
                cache.set(attempts_key, attempts, settings.LOGIN_ATTEMPTS_TIMEOUT)
                remaining = settings.LOGIN_ATTEMPTS_LIMIT - attempts
                error = f"اسم المستخدم أو كلمة المرور غير صحيحة — متبقي {remaining} محاولات"

    return render(request, "accounts/login.html", {"form": form, "error": error})
