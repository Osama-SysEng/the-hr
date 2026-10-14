"""
The H.R - Face Recognition Service
Biometric face recognition for attendance verification
"""

import base64
from dataclasses import dataclass
from typing import Any

from app.core.logging_utils import get_logger

import numpy as np

logger = get_logger(__name__)


def _tag(value: object) -> str:
    """Short opaque tag for identifiers in logs (no clear-text PII)."""
    import hashlib

    return hashlib.sha256(str(value).encode()).hexdigest()[:12]


@dataclass
class FaceRecognitionResult:
    matched: bool
    confidence: float
    employee_id: str | None = None
    employee_name: str | None = None
    face_encoding: list[float] | None = None
    message: str = ""


class FaceRecognitionService:
    """
    Face Recognition Service for attendance verification.
    Uses face_recognition library + OpenCV.
    Stores face encodings as mathematical vectors only (not raw images).
    """

    def __init__(self):
        self.known_encodings: dict[str, np.ndarray] = {}  # employee_id -> encoding
        self.known_names: dict[str, str] = {}  # employee_id -> name
        self.tolerance: float = 0.6

        # Try to import face_recognition library
        try:
            import face_recognition

            self.face_recognition_lib = face_recognition
        except ImportError:
            self.face_recognition_lib = None
            logger.warning("face_recognition library not available; biometric verification disabled")

        try:
            import cv2

            self.cv2 = cv2
        except ImportError:
            self.cv2 = None
            logger.warning("OpenCV not available; biometric verification disabled")

    def load_employee_face(self, employee_id: str, name: str, image_base64: str) -> bool:
        """
        Load and encode employee face from base64 image.
        Stores only the mathematical encoding vector (not the image).
        """
        if not self.face_recognition_lib:
            return False

        try:
            # Decode base64 image
            image_data = base64.b64decode(image_base64)
            np_array = np.frombuffer(image_data, np.uint8)
            image = self.cv2.imdecode(np_array, self.cv2.IMREAD_COLOR)

            if image is None:
                return False

            # Convert to RGB
            rgb_image = self.cv2.cvtColor(image, self.cv2.COLOR_BGR2RGB)

            # Get face encoding
            encodings = self.face_recognition_lib.face_encodings(rgb_image)

            if encodings:
                encoding = encodings[0]
                self.known_encodings[employee_id] = encoding
                self.known_names[employee_id] = name
                return True

            return False
        except Exception:
            logger.exception("Error loading face for %s", _tag(employee_id))
            return False

    def load_employee_face_from_file(self, employee_id: str, name: str, image_path: str) -> bool:
        """Load face encoding from image file."""
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
            return self.load_employee_face(employee_id, name, base64.b64encode(image_data).decode())
        except Exception:
            logger.exception("Error loading face from file")
            return False

    def recognize_face(self, image_base64: str) -> FaceRecognitionResult:
        """
        Recognize face in image against known employees.
        Returns match result with confidence score.
        """
        if not self.face_recognition_lib or not self.known_encodings:
            return FaceRecognitionResult(
                matched=False,
                confidence=0.0,
                message="Face recognition not available or no known faces",
            )

        try:
            # Decode image
            image_data = base64.b64decode(image_base64)
            np_array = np.frombuffer(image_data, np.uint8)
            image = self.cv2.imdecode(np_array, self.cv2.IMREAD_COLOR)

            if image is None:
                return FaceRecognitionResult(
                    matched=False,
                    confidence=0.0,
                    message="Unable to decode image",
                )

            # Convert to RGB
            rgb_image = self.cv2.cvtColor(image, self.cv2.COLOR_BGR2RGB)

            # Find faces
            face_locations = self.face_recognition_lib.face_locations(rgb_image)
            face_encodings = self.face_recognition_lib.face_encodings(rgb_image, face_locations)

            if not face_encodings:
                return FaceRecognitionResult(
                    matched=False,
                    confidence=0.0,
                    message="No face detected in image",
                )

            # Compare with known faces
            best_match = None
            best_confidence = 0.0

            for face_encoding in face_encodings:
                for employee_id, known_encoding in self.known_encodings.items():
                    matches = self.face_recognition_lib.compare_faces(
                        [known_encoding],
                        face_encoding,
                        tolerance=self.tolerance,
                    )

                    if matches[0]:
                        # Calculate confidence distance
                        distance = self.face_recognition_lib.face_distance(
                            [known_encoding],
                            face_encoding,
                        )[0]
                        confidence = 1 - distance

                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_match = employee_id

            if best_match:
                return FaceRecognitionResult(
                    matched=True,
                    confidence=round(best_confidence, 3),
                    employee_id=best_match,
                    employee_name=self.known_names.get(best_match, "Unknown"),
                    face_encoding=face_encodings[0].tolist(),
                    message=f"Face matched: {self.known_names.get(best_match, 'Unknown')}",
                )
            else:
                return FaceRecognitionResult(
                    matched=False,
                    confidence=0.0,
                    message="No matching face found in database",
                )

        except Exception as e:
            logger.exception("Error during face recognition")
            return FaceRecognitionResult(
                matched=False,
                confidence=0.0,
                message=f"Error during face recognition: {e!s}",
            )

    def get_face_encoding_from_image(self, image_base64: str) -> list[float] | None:
        """Extract face encoding from image (for enrollment)."""
        if not self.face_recognition_lib:
            return None

        try:
            image_data = base64.b64decode(image_base64)
            np_array = np.frombuffer(image_data, np.uint8)
            image = self.cv2.imdecode(np_array, self.cv2.IMREAD_COLOR)

            if image is None:
                return None

            rgb_image = self.cv2.cvtColor(image, self.cv2.COLOR_BGR2RGB)
            encodings = self.face_recognition_lib.face_encodings(rgb_image)

            if encodings:
                return encodings[0].tolist()

            return None
        except Exception:
            logger.exception("Face encoding extraction failed")
            return None

    def verify_liveness(self, image_base64: str) -> bool:
        """
        Simple liveness detection - check for multiple faces or blink detection.
        In production, use more sophisticated liveness detection.
        """
        if not self.face_recognition_lib:
            return True  # Skip liveness if library not available

        try:
            image_data = base64.b64decode(image_base64)
            np_array = np.frombuffer(image_data, np.uint8)
            image = self.cv2.imdecode(np_array, self.cv2.IMREAD_COLOR)

            if image is None:
                return False

            rgb_image = self.cv2.cvtColor(image, self.cv2.COLOR_BGR2RGB)
            face_locations = self.face_recognition_lib.face_locations(rgb_image)

            # Liveness check: exactly one face, reasonable size
            if len(face_locations) == 1:
                top, right, bottom, left = face_locations[0]
                face_height = bottom - top
                face_width = right - left

                # Face should be reasonable size (not too small, not too large)
                min_size = 50
                max_size = 500

                return min_size <= face_height <= max_size and min_size <= face_width <= max_size

            return False  # Multiple faces = potential spoofing
        except Exception:
            logger.exception("Liveness detection failed")
            return True

    def remove_employee(self, employee_id: str) -> bool:
        """Remove employee face data from database."""
        if employee_id in self.known_encodings:
            del self.known_encodings[employee_id]
            del self.known_names[employee_id]
            return True
        return False

    def get_all_employees(self) -> list[dict[str, Any]]:
        """Get list of all enrolled employees."""
        return [
            {
                "employee_id": emp_id,
                "name": name,
            }
            for emp_id, name in self.known_names.items()
        ]

    def get_encoding_count(self) -> int:
        """Get number of enrolled face encodings."""
        return len(self.known_encodings)
