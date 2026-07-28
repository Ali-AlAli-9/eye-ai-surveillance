import os
from ultralytics import YOLO


class ObjectDetector:
    def __init__(self, model_path="yolov8n.pt", confidence=0.5):
        if not os.path.isabs(model_path):
            model_path = os.path.join(os.path.dirname(__file__), model_path)
        self.model = YOLO(model_path)
        self.confidence = confidence

    def detect(self, frame):
        results = self.model.track(frame, verbose=False, persist=True)[0]
        detections = []

        for box in results.boxes:
            conf = float(box.conf[0])
            if conf < self.confidence:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls_id = int(box.cls[0])
            class_name = results.names[cls_id]
            track_id = int(box.id[0]) if box.id is not None and len(box.id) > 0 else None

            detections.append({
                "class": class_name,
                "confidence": round(conf, 2),
                "bbox": [x1, y1, x2, y2],
                "track_id": track_id,
            })

        return detections