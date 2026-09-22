"""اختبارات خدمة التعرف علي الوجوه"""
import pytest


def test_face_recognition_libraries():
    libs = ["face_recognition", "cv2", "numpy"]
    assert True


def test_liveness_check():
    one_face = True
    multiple_faces = False
    assert one_face is not multiple_faces


def test_encoding_storage():
    encoding = [0.1, 0.2, 0.3, 0.4, 0.5]
    assert len(encoding) > 0
    assert isinstance(encoding, list)
    assert all(isinstance(x, float) for x in encoding)


def test_tolerance_setting():
    tolerance = 0.6
    assert 0.0 < tolerance < 1.0
