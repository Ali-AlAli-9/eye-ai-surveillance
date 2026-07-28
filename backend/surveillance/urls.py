from django.urls import path
from . import views


urlpatterns = [
    
    path("",views.dashboard, name="dashboard"),
    path("live/", views.live, name="live"),
    path("history/", views.history, name="history"),
    path("alerts/", views.alerts, name="alerts"),
    path("alerts/<int:alert_id>/read/", views.mark_read, name="mark_read"),
    path("alerts/mark-all/", views.mark_all_read, name="mark_all_read"),
    path("history/delete/", views.delete_all_history, name="delete_history"),
    path("engine/start/", views.start_engine, name="start_engine"),
    path("engine/loading/", views.engine_loading, name="engine_loading"),
    path("engine/stop/", views.stop_engine, name="stop_engine"),
    path("api/check-db/", views.check_db_connection, name="check_db_connection"),
    path("manage-users/", views.manage_users, name="manage_users"),
    path("manage-users/reset/<int:user_id>/", views.reset_password, name="reset_password"),
    path("manage-users/logout/<int:user_id>/", views.force_logout, name="force_logout"),
    path("manage-users/delete/<int:user_id>/", views.delete_user, name="delete_user"),

]