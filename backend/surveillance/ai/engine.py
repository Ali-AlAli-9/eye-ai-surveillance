import cv2
import json
import base64
import logging
import threading
import time
import queue
from datetime import datetime
from asgiref.sync import async_to_sync
from django.core.cache import cache
from django.core.files.base import ContentFile
from surveillance.ai.camera import Camera
from surveillance.ai.motion import MotionDetector
from surveillance.ai.detector import ObjectDetector
from surveillance.models import Detection, Alert

logger = logging.getLogger("audit")


class AIEngine:

    def __init__(self, camera=None, motion_detector=None, object_detector=None,
                 face_recognizer=None, channel_layer=None, frame_skip=5):
        self.camera = camera or Camera(0)
        self.motion_detector = motion_detector or MotionDetector()
        self.object_detector = object_detector or ObjectDetector()
        self.face_recognizer = face_recognizer
        self.channel_layer = channel_layer
        self.frame_skip = frame_skip
        self._running = threading.Event()
        self._thread = None
        self._detect_thread = None
        self._lock = threading.Lock()
        self._capture_sessions = {}
        self._SESSION_TIMEOUT = 300
        self._MAX_FACE_IMAGES = 15
        self._MAX_BODY_IMAGES = 15
        self._CAPTURE_INTERVAL = 5
        self._FACE_CHECK_INTERVAL = 10
        self._face_check_counter = 0
        self._latest_frame = None
        self._frame_lock = threading.Lock()

    def start(self):
        if self._running.is_set():
            return
        self._running.set()
        cache.set("ai_engine_running", True, 300)
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running.clear()
        cache.set("ai_engine_running", False, 300)
        self._send_status(False)
        try:
            self.camera.release()
        except Exception:
            pass

    @property
    def is_running(self):
        return self._running.is_set()

    def _loop(self):
        if not self.camera.open():
            logger.warning("[AI] Camera failed to open")
            self._running.clear()
            cache.set("ai_engine_running", False, 300)
            self._send_status(False)
            return

        self._send_status(True)
        self._detect_thread = threading.Thread(target=self._detect_loop, daemon=True)
        self._detect_thread.start()

        while self._running.is_set():
            ret, frame = self.camera.read()
            if not ret or not self._running.is_set():
                break
            with self._frame_lock:
                self._latest_frame = frame.copy()
            self._send_stream_frame(frame)
            time.sleep(0.033)

    def _detect_loop(self):
        frame_count = 0
        while self._running.is_set():
            with self._frame_lock:
                frame = self._latest_frame
                if frame is not None:
                    frame = frame.copy()
            if frame is None:
                time.sleep(0.01)
                continue

            frame_count += 1
            if frame_count % (self.frame_skip + 1) != 0:
                time.sleep(0.01)
                continue

            try:
                has_motion = self.motion_detector.detect(frame)
            except Exception as e:
                logger.warning(f"[AI] Motion detection failed: {e}")
                has_motion = False

            if has_motion:
                self._process_frame(frame)

            time.sleep(0.01)

    def _send_stream_frame(self, frame):
        try:
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 40])
            b64 = base64.b64encode(buf).decode("utf-8")
            data = json.dumps({"image": b64, "detections": []})
            from surveillance.stream_queue import frame_queue
            if frame_queue.full():
                try:
                    frame_queue.get_nowait()
                except queue.Empty:
                    pass
            frame_queue.put_nowait(data)
        except Exception as e:
            logger.warning(f"[AI] Stream frame send failed: {e}")

    def _process_frame(self, frame):
        try:
            detections = self.object_detector.detect(frame)
        except Exception as e:
            logger.warning(f"[AI] Object detection failed: {e}")
            detections = []

        faces = []
        if self.face_recognizer:
            self._face_check_counter += 1
            if self._face_check_counter % self._FACE_CHECK_INTERVAL == 0:
                try:
                    faces = self.face_recognizer.recognize(frame)
                except Exception as e:
                    logger.warning(f"[AI] Face recognition failed: {e}")
                    faces = []

        if not detections and not faces:
            return

        person_dets = [d for d in detections if d["class"] == "person"]
        self._update_sessions()

        if person_dets and faces:
            self._handle_person_with_face(frame, person_dets, faces)
        elif person_dets:
            self._handle_person_no_face(frame, person_dets)

    def _get_or_create_session(self, hash_key):
        if hash_key not in self._capture_sessions:
            self._capture_sessions[hash_key] = {
                "face_count": 0,
                "body_count": 0,
                "last_capture": 0.0,
                "alert_sent": False,
            }
        return self._capture_sessions[hash_key]

    def _update_sessions(self):
        now = time.time()
        expired = [
            h for h, s in self._capture_sessions.items()
            if s["last_capture"] > 0 and now - s["last_capture"] > self._SESSION_TIMEOUT
        ]
        for h in expired:
            del self._capture_sessions[h]

    def _handle_person_with_face(self, frame, person_dets, faces):
        for d in person_dets[:5]:
            track_id = d.get("track_id")
            if track_id is None:
                self._handle_body_capture(frame, d)
                continue

            px1, py1, px2, py2 = d["bbox"]
            matched_face = None
            for f in faces:
                fx1, fy1, fx2, fy2 = f["bbox"]
                fcx = (fx1 + fx2) // 2
                fcy = (fy1 + fy2) // 2
                if px1 <= fcx <= px2 and py1 <= fcy <= py2:
                    matched_face = f
                    break

            if not matched_face:
                self._handle_body_capture(frame, d)
                continue

            person_hash = matched_face["person_hash"]
            import numpy as np
            enc_bytes = matched_face["encoding"].astype(np.float32).tobytes()
            session_key = f"person_{person_hash}"
            session = self._get_or_create_session(session_key)

            if not session["alert_sent"]:
                try:
                    is_new = not Detection.objects.filter(person_hash=person_hash).exists()
                except Exception:
                    is_new = True
                alert_type = "person_stranger" if is_new else "person_known"
                label = "شخص جديد" if is_new else "شخص معروف"
                self._create_alert(
                    alert_type,
                    f"تم اكتشاف {label} — ثقة {d['confidence']:.2f}",
                    frame,
                )
                session["alert_sent"] = True

            now = time.time()
            if now - session["last_capture"] < self._CAPTURE_INTERVAL:
                continue

            if session["face_count"] < self._MAX_FACE_IMAGES:
                success = self._create_detection(frame, d, enc_bytes, person_hash)
                if success:
                    session["face_count"] += 1
                    session["last_capture"] = now
            elif session["body_count"] < self._MAX_BODY_IMAGES:
                success = self._create_detection(frame, d, None, person_hash)
                if success:
                    session["body_count"] += 1
                    session["last_capture"] = now

    def _handle_person_no_face(self, frame, person_dets):
        for d in person_dets[:5]:
            track_id = d.get("track_id")
            if track_id is None:
                continue

            session_key = f"person_{track_id}"
            session = self._get_or_create_session(session_key)

            if not session["alert_sent"]:
                self._create_alert(
                    "motion",
                    f"تم اكتشاف جسم متحرك — ثقة {d['confidence']:.2f}",
                    frame,
                )
                session["alert_sent"] = True

            now = time.time()
            if now - session["last_capture"] < self._CAPTURE_INTERVAL:
                continue

            if session["body_count"] < self._MAX_BODY_IMAGES:
                success = self._create_detection(frame, d, None, None)
                if success:
                    session["body_count"] += 1
                    session["last_capture"] = now

    def _handle_body_capture(self, frame, det):
        track_id = det.get("track_id")
        if track_id is None:
            return

        session_key = f"person_{track_id}"
        session = self._get_or_create_session(session_key)

        if not session["alert_sent"]:
            self._create_alert(
                "motion",
                f"تم اكتشاف جسم متحرك — ثقة {det['confidence']:.2f}",
                frame,
            )
            session["alert_sent"] = True

        now = time.time()
        if now - session["last_capture"] < self._CAPTURE_INTERVAL:
            return

        if session["body_count"] < self._MAX_BODY_IMAGES:
            success = self._create_detection(frame, det, None, None)
            if success:
                session["body_count"] += 1
                session["last_capture"] = now

    def _create_detection(self, frame, det, face_encoding_bytes, person_hash):
        try:
            x1, y1, x2, y2 = det["bbox"]
            h, w = frame.shape[:2]
            crop = frame[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
            if crop.size == 0:
                crop = cv2.resize(frame, (320, 240))
            _, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 80])
            snap = ContentFile(
                buf.tobytes(),
                name=f"snap_{datetime.now().strftime('%H%M%S%f')}_{det['confidence']:.2f}.jpg",
            )

            det_class = det["class"]
            det_confidence = det["confidence"]
            det_bbox = list(det["bbox"])

            def _save():
                try:
                    Detection.objects.create(
                        class_name=det_class,
                        confidence=det_confidence,
                        bbox_x1=det_bbox[0],
                        bbox_y1=det_bbox[1],
                        bbox_x2=det_bbox[2],
                        bbox_y2=det_bbox[3],
                        snapshot=snap,
                        face_encoding=face_encoding_bytes,
                        person_hash=person_hash,
                    )
                except Exception as e:
                    logger.warning(f"[AI] Detection save failed: {e}")

            threading.Thread(target=_save, daemon=True).start()
            return True
        except Exception as e:
            logger.warning(f"[AI] Detection prepare failed: {e}")
            return False

    def _create_alert(self, alert_type, message, frame):
        try:
            small = cv2.resize(frame, (320, 240))
            _, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 70])
            alert_snap = ContentFile(
                buf.tobytes(),
                name=f"alert_{datetime.now().strftime('%H%M%S%f')}.jpg",
            )

            def _save():
                try:
                    Alert.objects.create(
                        alert_type=alert_type, message=message, snapshot=alert_snap
                    )
                    cache.delete("unread_alert_count")
                except Exception as e:
                    logger.warning(f"[AI] Alert save failed: {e}")

            threading.Thread(target=_save, daemon=True).start()
        except Exception as e:
            logger.warning(f"[AI] Alert prepare failed: {e}")

    def _send_status(self, running):
        if not self.channel_layer:
            return
        try:
            data = json.dumps({"type": "status", "running": running})
            async_to_sync(self.channel_layer.group_send)(
                "live_stream", {"type": "engine.status", "data": data},
            )
        except Exception as e:
            logger.warning(f"[AI] Status send failed: {e}")
