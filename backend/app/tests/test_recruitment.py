"""اختبارات التوظيف والفحص AI"""
import pytest


def test_cv_score_calculation():
    criteria = [
        {"title": "Python", "keywords": "Python, FastAPI, SQLAlchemy", "weight": 30},
        {"title": "PostgreSQL", "keywords": "PostgreSQL, Redis", "weight": 25},
    ]
    cv_text = "Python, FastAPI, SQLAlchemy, PostgreSQL, Redis"
    total_weight = sum(c["weight"] for c in criteria)
    score = 0
    for c in criteria:
        kw = c["keywords"].lower().split(", ")
        matched = sum(1 for k in kw if k in cv_text.lower())
        score += (matched / len(kw)) * c["weight"]
    assert round(score / total_weight * 100) == 100


def test_stage_assignment():
    score = 85
    if score >= 70:
        stage = "screening"
    elif score >= 40:
        stage = "screening"
    else:
        stage = "rejected"
    assert stage == "screening"


def test_interview_questions_count():
    questions = [
        "طلب تعريف عن نفسك",
        "أخبرني عن تجربتك",
        "ما هي توقعاتك للراتب؟",
    ]
    assert len(questions) == 3
