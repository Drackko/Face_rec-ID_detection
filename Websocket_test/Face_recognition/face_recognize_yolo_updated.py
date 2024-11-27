import cv2
import numpy as np
import torch
from ultralytics import YOLO
from torchvision import transforms
from .face_recognition.arcface.model import iresnet_inference
from .face_recognition.arcface.utils import compare_encodings, read_features
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from collections import defaultdict
import time

# Track face states
face_tracker = defaultdict(lambda: {"state": "UNDETERMINED", "last_seen": time.time(), "box": None})
timeout = 3  # seconds before marking as UNKNOWN
lost_threshold = 5  # seconds before removing from the tracker


# Device configuration
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# YOLO model initialization
yolo_model = YOLO(os.path.join(BASE_DIR,"face_detection","yolo","weights","yolo11n-face.pt"))

# ArcFace model initialization

recognizer = iresnet_inference(
    model_name="r100",
    path=os.path.join(
        BASE_DIR, "face_recognition", "arcface", "weights", "arcface_r100.pth"
    ),
    device=device,
)
# Preloaded face embeddings and names
images_names, images_embs = read_features(
    feature_path=os.path.join(
        BASE_DIR, "datasets", "face_features", "arcface100_feature"
    )
)
# Preprocessing for ArcFace input
face_preprocess = transforms.Compose([
    transforms.ToTensor(),
    transforms.Resize((112, 112)),
    transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
])



def get_face_embedding(face_image):
    """Extract features for a given face image."""
    face_image = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
    face_tensor = face_preprocess(face_image).unsqueeze(0).to(device)
    emb = recognizer(face_tensor).cpu().detach().numpy()
    return emb / np.linalg.norm(emb)


def face_rec(face_image):
    """Match face image against known embeddings."""
    query_emb = get_face_embedding(face_image)
    score, id_min = compare_encodings(query_emb, images_embs)
    return score, images_names[id_min] if score > 0.5 else None


def is_face_in_person_box(face_box, person_box, iou_threshold=0.5):
    """Check if a face bounding box is within a person bounding box."""
    x1 = max(face_box[0], person_box[0])
    y1 = max(face_box[1], person_box[1])
    x2 = min(face_box[2], person_box[2])
    y2 = min(face_box[3], person_box[3])

    if x2 <= x1 or y2 <= y1:
        return False

    face_area = (face_box[2] - face_box[0]) * (face_box[3] - face_box[1])
    intersection_area = (x2 - x1) * (y2 - y1)

    return intersection_area / face_area > iou_threshold

def recognize_faces_in_persons(frame, person_bboxes):
    """
    Detect faces within person bounding boxes and classify them as SIETIAN, UNKNOWN, or UNDETERMINED.
    Args:
        frame: The video frame to process.
        person_bboxes: List of person bounding boxes in the format [(x1, y1), (x2, y2)].
    Returns:
        modified_frame: Frame with person bounding boxes and recognition results.
        states: List of states for each person box - SIETIAN, UNKNOWN, or UNDETERMINED.
    """
    global face_tracker

    # Detect faces using YOLO
    face_results = yolo_model.predict(frame, conf=0.5)
    face_boxes = [
        list(map(int, bbox)) for result in face_results for bbox in result.boxes.xyxy
    ]

    # Initialize states for person bounding boxes
    states = ["UNDETERMINED"] * len(person_bboxes)

    # Process each detected face
    current_time = time.time()
    updated_faces = set()

    for face_box in face_boxes:
        # Generate a temporary ID for the face using the bounding box
        face_id = tuple(face_box)  # Simple ID based on coordinates
        updated_faces.add(face_id)

        # Crop and preprocess the face image
        x1, y1, x2, y2 = face_box
        cropped_face = frame[y1:y2, x1:x2]
        score, name = face_rec(cropped_face)

        # Update tracker
        if face_id in face_tracker:
            face_tracker[face_id]["last_seen"] = current_time
            face_tracker[face_id]["box"] = face_box
        else:
            face_tracker[face_id] = {"state": "UNDETERMINED", "last_seen": current_time, "box": face_box}

        # Determine the state based on recognition
        if name:
            face_tracker[face_id]["state"] = f"SIETIAN ({name})"
        elif current_time - face_tracker[face_id]["last_seen"] > timeout:
            face_tracker[face_id]["state"] = "UNKNOWN"

        # Draw bounding box and state
        color = (0, 255, 0) if "SIETIAN" in face_tracker[face_id]["state"] else (0, 0, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            frame,
            face_tracker[face_id]["state"],
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            color,
            2,
        )

    # Cleanup: Remove lost faces
    lost_faces = [face_id for face_id, data in face_tracker.items() if current_time - data["last_seen"] > lost_threshold]
    for face_id in lost_faces:
        del face_tracker[face_id]

    # Check person bounding boxes for state updates
    for idx, person_box in enumerate(person_bboxes):
        for face_id, face_data in face_tracker.items():
            if is_face_in_person_box(face_data["box"], person_box):
                states[idx] = face_data["state"]
                break

    return frame, states
