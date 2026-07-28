import os
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from surveillance.models import Detection, Alert


class Command(BaseCommand):
    help = "حذف البيانات والصور الأقدم من 48 ساعة"

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=48)
        count_det = 0
        count_alert = 0

        for d in Detection.objects.filter(timestamp__lt=cutoff).iterator():
            if d.snapshot:
                try:
                    if os.path.isfile(d.snapshot.path):
                        os.remove(d.snapshot.path)
                except (ValueError, OSError):
                    pass
            count_det += 1
        Detection.objects.filter(timestamp__lt=cutoff).delete()

        for a in Alert.objects.filter(timestamp__lt=cutoff).iterator():
            if a.snapshot:
                try:
                    if os.path.isfile(a.snapshot.path):
                        os.remove(a.snapshot.path)
                except (ValueError, OSError):
                    pass
            count_alert += 1
        Alert.objects.filter(timestamp__lt=cutoff).delete()

        self.stdout.write(self.style.SUCCESS(
            f"تم الحذف: {count_det} Detection, {count_alert} Alert (مع الصور)"
        ))
