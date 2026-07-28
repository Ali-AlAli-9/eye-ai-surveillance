import cv2
import torch
import hashlib
import numpy as np
from facenet_pytorch import MTCNN, InceptionResnetV1


class FaceRecognizer:

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.mtcnn = MTCNN(
            keep_all=True,
            device=self.device,
            min_face_size=40,
            thresholds=[0.6, 0.7, 0.7],
            post_process=True,
        )
        self.resnet = InceptionResnetV1(pretrained="vggface2").eval().to(self.device)

    def recognize(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        boxes, probs = self.mtcnn.detect(rgb)

        if boxes is None:
            return []

        faces = []
        for box, prob in zip(boxes, probs):
            try:
                if prob < 0.9:
                    continue

                x1, y1, x2, y2 = map(int, box)
                h, w = rgb.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)

                face_crop = rgb[y1:y2, x1:x2]
                if face_crop.size == 0:
                    continue

                face_tensor = torch.from_numpy(face_crop).permute(2, 0, 1).float()
                face_tensor = torch.nn.functional.interpolate(
                    face_tensor.unsqueeze(0), size=(160, 160), mode="bilinear", align_corners=False
                )
                face_tensor = face_tensor.to(self.device)

                with torch.no_grad():
                    embedding = self.resnet(face_tensor)

                enc_np = embedding.cpu().numpy().flatten()
                enc_bytes = enc_np.astype(np.float32).tobytes()
                person_hash = hashlib.sha256(enc_bytes).hexdigest()[:16]

                faces.append({
                    "bbox": [x1, y1, x2, y2],
                    "encoding": enc_np,
                    "person_hash": person_hash,
                    "name": "unknown",
                    "confidence": float(prob),
                })
            except Exception:
                continue

        return faces