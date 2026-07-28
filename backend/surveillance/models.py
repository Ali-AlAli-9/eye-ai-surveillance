from django.db import models
import hashlib


class Detection(models.Model):
    class_name = models.CharField(max_length=100)
    confidence = models.FloatField()
    bbox_x1 = models.IntegerField()
    bbox_y1 = models.IntegerField()
    bbox_x2 = models.IntegerField()
    bbox_y2 = models.IntegerField()
    snapshot = models.ImageField(upload_to="snapshots/", null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    face_encoding = models.BinaryField(null=True, blank=True)
    person_hash = models.CharField(max_length=64, db_index=True, null=True, blank=True)
    
    
    def __str__(self):
        return f"{self.class_name} ({self.confidence:.2f}) @ {self.timestamp}"

    
    def get_person_hash(self):
        if self.face_encoding:
            return hashlib.sha256(bytes(self.face_encoding)).hexdigest()
        return None


class Alert(models.Model):
    ALERT_TYPES = [
    ("motion", "حركة"),
    ("person", "شخص"),
    ("person_stranger", "شخص غريب"),
    ("person_known", "شخص معروف"),
   ]
    
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    message = models.TextField()
    snapshot = models.ImageField(upload_to="alerts/", null=True, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"[{self.get_alert_type_display()}] {self.timestamp}"