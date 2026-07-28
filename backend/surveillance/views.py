from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.core.cache import cache
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.cache import never_cache
from .models import Detection, Alert
from .forms import CreateUserForm
import logging

audit = logging.getLogger("audit")


@login_required
@require_GET
def check_db_connection(request):
    from django.conf import settings
    if getattr(settings, 'IS_LOCAL_DB', True):
        return JsonResponse({"status": "ok"})
    from django.db import connection
    try:
        connection.ensure_connection()
        return JsonResponse({"status": "ok"})
    except Exception:
        return JsonResponse({"status": "error"}, status=503)


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def start_engine(request):
    from surveillance.ai.engine_instance import get_engine, set_engine, set_booting
    import threading
    engine = get_engine()
    if engine and engine.is_running:
        return redirect("dashboard")

    username = request.user.username
    set_booting(True)

    def _boot():
        try:
            from channels.layers import get_channel_layer
            from surveillance.ai.engine import AIEngine
            from surveillance.ai.recognizer import FaceRecognizer
            cl = get_channel_layer()
            fr = FaceRecognizer()
            engine = AIEngine(channel_layer=cl, face_recognizer=fr)
            engine.start()
            set_engine(engine)
            audit.warning(f"ENGINE_STARTED by {username}")
            print(f"[AI] ENGINE_STARTED by {username}")
        except Exception as ex:
            audit.error(f"ENGINE_FAILED: {ex}")
            print(f"[AI] ENGINE_FAILED: {ex}")
            import traceback
            traceback.print_exc()
        finally:
            set_booting(False)

    threading.Thread(target=_boot, daemon=True).start()
    return redirect("engine_loading")


@login_required
@user_passes_test(lambda u: u.is_staff)
@never_cache
def engine_loading(request):
    return render(request, 'surveillance/engine_loading.html')


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def stop_engine(request):
    from surveillance.ai.engine_instance import get_engine, clear_engine
    engine = get_engine()
    if engine and engine.is_running:
        engine.stop()
        clear_engine()
        audit.warning(f"ENGINE_STOPPED by {request.user.username}")
    return redirect("dashboard")


@login_required
@never_cache
def dashboard(request):
    from datetime import timedelta
    from django.utils import timezone
    from django.db.models import Count
    from surveillance.ai.engine_instance import get_engine
    today = timezone.now() - timedelta(hours=24)
    alerts = Alert.objects.order_by("-timestamp")[:5]
    today_count = Detection.objects.filter(
        timestamp__gte=today,
        class_name="person"
    ).count()
    last_detection = Detection.objects.order_by("-timestamp").first()
    engine = get_engine()
    engine_running = engine is not None and engine.is_running
    return render(request, 'surveillance/dashboard.html', {
        "alerts": alerts,
        "today_count": today_count,
        "last_detection": last_detection,
        "engine_running": engine_running,
        "is_staff": request.user.is_staff,
        "is_superuser": request.user.is_superuser,
    })

@login_required
def live(request):
    from surveillance.ai.engine_instance import get_engine
    engine = get_engine()
    engine_running = engine is not None and engine.is_running
    return render(request, 'surveillance/live.html', {"engine_running": engine_running})

@login_required
def history(request):
    class_filter = request.GET.get("class", "")
    detections_list = Detection.objects.order_by("-timestamp")
    if class_filter:
        detections_list = detections_list.filter(class_name=class_filter)
    classes = Detection.objects.values_list("class_name", flat=True).distinct()
    paginator = Paginator(detections_list, 25)
    page = request.GET.get("page")
    detections = paginator.get_page(page)
    return render(request, 'surveillance/history.html', {
        "detections": detections,
        "classes": classes,
        "selected_class": class_filter,
    })

@login_required
def alerts(request):
    alerts_list = Alert.objects.order_by("-timestamp")
    paginator = Paginator(alerts_list, 50)
    page = request.GET.get("page")
    alerts = paginator.get_page(page)
    return render(request, 'surveillance/alerts.html', {"alerts": alerts})

@login_required
@require_POST
def mark_read(request, alert_id):
    alert = get_object_or_404(Alert, id=alert_id)
    alert.is_read = True
    alert.save()
    cache.delete("unread_alert_count")
    return redirect("alerts")

@login_required
@require_POST
def mark_all_read(request):
    Alert.objects.filter(is_read=False).update(is_read=True)
    cache.delete("unread_alert_count")
    return redirect("alerts")

@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def delete_all_history(request):
    import secrets
    confirm = request.POST.get("confirm_delete")
    if confirm != "DELETE_ALL":
        return redirect("history")
    Detection.objects.all().delete()
    audit.warning(f"ALL_HISTORY_DELETED by {request.user.username}")
    return redirect("history")


@login_required
@user_passes_test(lambda u: u.is_staff)
def manage_users(request):
    if request.user.is_superuser:
        users_list = User.objects.all().order_by("date_joined")
    else:
        users_list = User.objects.filter(is_superuser=False).order_by("date_joined")
    paginator = Paginator(users_list, 20)
    page = request.GET.get("page")
    users = paginator.get_page(page)
    form = CreateUserForm()
    success = None
    error = None

    if request.method == "POST":
        form = CreateUserForm(request.POST)
        if form.is_valid():
            form.save()
            created_name = form.cleaned_data.get("username", "?")
            audit.warning(f"USER_CREATED by {request.user.username}: {created_name}")
            form = CreateUserForm()
            success = "تم إنشاء المستخدم بنجاح"
        else:
            errors_list = []
            for field, errs in form.errors.items():
                for e in errs:
                    errors_list.append(e)
            error = " | ".join(errors_list)

    return render(request, "surveillance/manage_users.html", {
        "users": users,
        "form": form,
        "success": success,
        "error": error,
    })

@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def reset_password(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user.is_superuser and not request.user.is_superuser:
        return redirect("manage_users")
    new_password = request.POST.get("new_password", "")
    confirm_password = request.POST.get("confirm_new_password", "")
    if not new_password or not confirm_password:
        return redirect("manage_users")
    if new_password != confirm_password:
        return redirect("manage_users")
    try:
        validate_password(new_password, user=user)
    except ValidationError:
        return redirect("manage_users")
    user.set_password(new_password)
    user.save()
    Session.objects.filter(session_data__contains=f"_auth_user_id").filter(
        session_data__contains=str(user.id)
    ).delete()
    audit.warning(f"PASSWORD_RESET by {request.user.username} for user {user.username}")
    return redirect("manage_users")

@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def force_logout(request, user_id):
    user = get_object_or_404(User, id=user_id)
    Session.objects.filter(session_data__contains=str(user.id)).delete()
    audit.warning(f"FORCE_LOGOUT by {request.user.username} for user {user.username}")
    return redirect("manage_users")



@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def delete_user(request, user_id):
    target = get_object_or_404(User, id=user_id)
    if target.id == request.user.id:
        return redirect("manage_users")
    if target.is_superuser and not request.user.is_superuser:
        return redirect("manage_users")
    Session.objects.filter(session_data__contains=str(target.id)).delete()
    audit.warning(f"USER_DELETED by {request.user.username}: {target.username}")
    target.delete()
    return redirect("manage_users")