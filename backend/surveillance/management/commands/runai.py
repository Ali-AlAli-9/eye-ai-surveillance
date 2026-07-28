import platform
import signal
import sys
import time

from channels.layers import get_channel_layer
from django.core.management.base import BaseCommand

from surveillance.ai.engine import AIEngine
from surveillance.ai.recognizer import FaceRecognizer

engine = None


class Command(BaseCommand):
    help = "تشغيل AI Engine (كاميرا + كشف + WebSocket)"

    def handle(self, *args, **options):
        global engine

        channel_layer = get_channel_layer()
        face_recognizer = FaceRecognizer()
        engine = AIEngine(
            channel_layer=channel_layer,
            face_recognizer=face_recognizer,
        )
        engine.start()

        if not engine.is_running:
            self.stdout.write(self.style.ERROR("فشل تشغيل AI Engine - تحقق من الكاميرا"))
            return

        self.stdout.write(self.style.SUCCESS("✅ AI Engine بدأ"))

        def shutdown(signum, frame):
            self.stdout.write("\n⏹️  إيقاف AI Engine...")
            engine.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, shutdown)
        if platform.system() != "Windows":
            signal.signal(signal.SIGTERM, shutdown)

        try:
            while engine.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            engine.stop()