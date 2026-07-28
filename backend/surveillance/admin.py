from django.contrib import admin
from .models import Detection, Alert

@admin.register(Detection)
class DetectionAdmin(admin.ModelAdmin):
    list_display = ["class_name", "confidence", "timestamp"]
    list_filter = ["class_name"]

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ["alert_type", "is_read", "timestamp"]
    list_filter = ["alert_type", "is_read"]
    
    
    