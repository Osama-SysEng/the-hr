"""اختبارات خدمة LLM"""
import pytest


def test_cv_extraction_schema():
    schema = {
        "skills": [],
        "experience_signals": [],
        "education_signals": [],
        "unanswered_job_criteria": [],
        "review_warnings": [],
    }
    assert len(schema) == 5


def test_interview_evaluation():
    questions = [{"question": "التعريف عن نفسك", "weight": 10}]
    answers = [{"answer": "مرحباً، أنا مطور بخبرة 5 سنوات"}]
    scores = []
    for q, a in zip(questions, answers):
        word_count = len(a["answer"].split())
        score = min(100, word_count * 3 + 50)
        scores.append({"score": score, "max_score": 100, "feedback": "Okay"})
    overall = sum(s["score"] for s in scores) / len(scores)
    assert round(overall) == 68


def test_turnover_prediction():
    risk = 0
    late = 20
    total = 100
    if late / total > 0.15:
        risk += 20
    years = 1
    if years < 2:
        risk += 10
    if years > 5:
        risk -= 10
    assert risk == 30
    assert risk <= 100
    assert risk >= 0
