"""
The H.R - LLM Service
AI-powered CV extraction, interview evaluation, and predictions
"""

import os
import json
import hashlib
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from openai import OpenAI

try:
    import google.generativeai as genai
except ImportError:  # Optional dependency — Gemini disabled without it
    genai = None


@dataclass
class SkillEvidence:
    skill: str
    evidence: str
    confidence: str  # "high", "medium", "low"


@dataclass
class ResumeExtraction:
    skills: List[SkillEvidence]
    experience_signals: List[str]
    education_signals: List[str]
    unanswered_job_criteria: List[str]
    review_warnings: List[str]


class LLMService:
    """
    Service for AI-powered text analysis.
    Supports OpenAI (GPT-4o-mini) and Google Gemini.
    """

    def __init__(self):
        self.openai_client: Optional[OpenAI] = None
        self.gemini_client = None
        self.use_openai = os.environ.get("OPENAI_API_KEY")
        self.use_gemini = os.environ.get("GEMINI_API_KEY")

        if self.use_openai:
            self.openai_client = OpenAI(api_key=self.use_openai)

        if self.use_gemini and genai is not None:
            genai.configure(api_key=self.use_gemini)
            self.gemini_client = genai.GenerativeModel('gemini-1.5-pro')

    def extract_cv_facts(
        self,
        cv_text: str,
        job_criteria: List[str],
        model: str = "gpt-4o-mini",
    ) -> Optional[ResumeExtraction]:
        """
        Extract job-relevant facts from CV text using LLM.
        Returns structured extraction with skills, experience, education signals.
        """
        if not cv_text:
            return None

        criteria_text = "\n".join(f"- {c}" for c in job_criteria)

        system_prompt = """You are an HR assistant extracting job-relevant information from a CV.
Extract ONLY facts explicitly supported by the CV text.
Do NOT infer or return: age, gender, nationality, religion, disability, health, family status,
ethnicity, personality, protected traits, salary expectations, employability, recommendations.
For each skill, provide a direct quote from the CV as evidence.
Mark ambiguity for human review.
Return ONLY valid JSON matching the schema."""

        
        prompt = f"""Job criteria:\n{criteria_text}\n\nCV text:\n{cv_text}"""

        if self.use_openai and self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "resume_extraction",
                            "strict": True,
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "skills": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "skill": {"type": "string"},
                                                "evidence": {"type": "string"},
                                                "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                                            },
                                            "required": ["skill", "evidence", "confidence"],
                                            "additionalProperties": False,
                                        },
                                    },
                                    "experience_signals": {"type": "array", "items": {"type": "string"}},
                                    "education_signals": {"type": "array", "items": {"type": "string"}},
                                    "unanswered_job_criteria": {"type": "array", "items": {"type": "string"}},
                                    "review_warnings": {"type": "array", "items": {"type": "string"}},
                                },
                                "required": [
                                    "skills", "experience_signals", "education_signals",
                                    "unanswered_job_criteria", "review_warnings",
                                ],
                                "additionalProperties": False,
                            },
                        },
                    },
                    temperature=0.3,
                    max_tokens=2000,
                )

                result = json.loads(response.choices[0].message.content)
                return ResumeExtraction(
                    skills=[
                        SkillEvidence(
                            skill=s["skill"],
                            evidence=s["evidence"],
                            confidence=s["confidence"],
                        )
                        for s in result.get("skills", [])
                    ],
                    experience_signals=result.get("experience_signals", []),
                    education_signals=result.get("education_signals", []),
                    unanswered_job_criteria=result.get("unanswered_job_criteria", []),
                    review_warnings=result.get("review_warnings", []),
                )
            except Exception as e:
                print(f"OpenAI extraction failed: {e}")
                return None

        elif self.use_gemini and self.gemini_client:
            try:
                prompt = f"{system_prompt}\n\n{user_prompt}"
                response = self.gemini_client.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=2000,
                    ),
                )
                result = json.loads(response.text)
                return ResumeExtraction(
                    skills=[
                        SkillEvidence(
                            skill=s["skill"],
                            evidence=s["evidence"],
                            confidence=s["confidence"],
                        )
                        for s in result.get("skills", [])
                    ],
                    experience_signals=result.get("experience_signals", []),
                    education_signals=result.get("education_signals", []),
                    unanswered_job_criteria=result.get("unanswered_job_criteria", []),
                    review_warnings=result.get("review_warnings", []),
                )
            except Exception as e:
                print(f"Gemini extraction failed: {e}")
                return None

        return None

    def evaluate_interview_answers(
        self,
        questions: List[Dict[str, Any]],
        answers: List[Dict[str, Any]],
        job_title: str = "",
    ) -> Dict[str, Any]:
        """
        Evaluate interview answers using AI.
        Returns overall score and per-question breakdown.
        """
        if not self.use_openai and not self.use_gemini:
            # Return simple heuristic evaluation
            return self._heuristic_evaluation(questions, answers)

        combined = []
        for q, a in zip(questions, answers):
            combined.append(f"Q: {q.get('question', '')}\nA: {a.get('answer', '')}")

        prompt = f"""Evaluate these interview answers for the position of: {job_title}

Analyze each answer for:
1. Content quality and relevance (0-40 points)
2. Communication clarity (0-25 points)
3. Technical accuracy (0-20 points)
4. Enthusiasm and cultural fit signals (0-15 points)

Return JSON:
{{
  "overall_score": <0-100>,
  "by_question": [
    {{
      "question_id": "<id>",
      "score": <0-100>,
      "max_score": 100,
      "feedback": "<brief feedback>"
    }}
  ],
  "strengths": ["<strength 1>", "<strength 2>"],
  "weaknesses": ["<weakness 1>", "<weakness 2>"],
  "recommendation": "strong_candidate" | "needs_review" | "not_suitable"
}}

Answers:
{"\n".join(combined)}
"""

        if self.use_openai and self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert HR interviewer. Provide fair, objective evaluations."},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_schema"},
                    temperature=0.4,
                    max_tokens=1500,
                )
                return json.loads(response.choices[0].message.content)
            except Exception:
                return self._heuristic_evaluation(questions, answers)

        elif self.use_gemini and self.gemini_client:
            try:
                response = self.gemini_client.generate_content(prompt)
                return json.loads(response.text)
            except Exception:
                return self._heuristic_evaluation(questions, answers)

        return self._heuristic_evaluation(questions, answers)

    def _heuristic_evaluation(
        self,
        questions: List[Dict[str, Any]],
        answers: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Simple heuristic evaluation when AI is not available."""
        scores = []
        for q, a in zip(questions, answers):
            answer_text = a.get("answer", "")
            word_count = len(answer_text.split())
            score = min(100, word_count * 3 + (50 if word_count > 20 else 0))
            scores.append({
                "question_id": q.get("id", ""),
                "score": score,
                "max_score": 100,
                "feedback": "Answer provided" if word_count > 0 else "No answer",
            })

        overall = round(sum(s["score"] for s in scores) / len(scores)) if scores else 0

        return {
            "overall_score": overall,
            "by_question": scores,
            "strengths": ["Answers provided"] if any(a.get("answer") for a in answers) else [],
            "weaknesses": ["AI evaluation not available"] if not self.use_openai and not self.use_gemini else [],
            "recommendation": "needs_review",
        }

    def generate_interview_questions(
        self,
        job_title: str,
        job_description: str,
        required_skills: List[str],
        experience_level: str = "mid",
        num_questions: int = 8,
    ) -> List[Dict[str, Any]]:
        """
        Generate role-specific interview questions.
        """
        question_types = [
            "introduction",
            "experience",
            "technical",
            "problem_solving",
            "behavioral",
            "cultural_fit",
        ]

        questions = []
        question_id = 0

        # Introduction
        questions.append({
            "id": f"q-{question_id}",
            "question": "مرحباً بك! رحب بك؟ تخبرني عن نفسك وبخبرتك العمل في هذا المجال؟",
            "type": "text",
            "max_time_minutes": 3,
            "role": "introduction",
            "weight": 10,
        })
        question_id += 1

        # Experience
        questions.append({
            "id": f"q-{question_id}",
            "question": "ما هي أبرز الإنجازات في مسيرتك المهنية؟ شارك معي مثالًا محددًا؟",
            "type": "text",
            "max_time_minutes": 3,
            "role": "experience",
            "weight": 15,
        })
        question_id += 1

        # Technical questions
        for skill in required_skills[:3]:
            questions.append({
                "id": f"q-{question_id}",
                "question": f"أخبرني عن خبرتك العملية في {skill}؟ ما هي أهم المشاريع التي استخدمت فيها هذه المهارة؟",
                "type": "text",
                "max_time_minutes": 3,
                "role": "technical",
                "weight": 20,
            })
            question_id += 1

        # Problem solving
        questions.append({
            "id": f"q-{question_id}",
            "question": "صف لي موقفًا واجهت فيه تحديًا تقنيًا كبيرًا وكيف تغلبت عليه؟",
            "type": "text",
            "max_time_minutes": 3,
            "role": "problem_solving",
            "weight": 20,
        })
        question_id += 1

        # Behavioral
        questions.append({
            "id": f"q-{question_id}",
            "question": " كيف تتعامل مع الضغط؟ شارك معي مثالًا عندما كنت تحت ضغط كبير؟",
            "type": "text",
            "max_time_minutes": 3,
            "role": "behavioral",
            "weight": 15,
        })
        question_id += 1

        # Cultural fit
        questions.append({
            "id": f"q-{question_id}",
            "question": "لماذا ترغب في العمل في هذه الشركة وفي هذه الدور تحديدًا؟",
            "type": "text",
            "max_time_minutes": 2,
            "role": "cultural_fit",
            "weight": 10,
        })
        question_id += 1

        # Language
        questions.append({
            "id": f"q-{question_id}",
            "question": "ما هي لغات البرمجة وال بيئات التطوير التي تفضلها ولماذا؟",
            "type": "text",
            "max_time_minutes": 2,
            "role": "technical",
            "weight": 10,
        })

        return questions[:num_questions]

    def predict_turnover_risk(
        self,
        employee_data: Dict[str, Any],
        attendance_history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Predict employee turnover risk based on attendance patterns and employee data.
        """
        # Simple heuristic prediction
        risk_score = 0
        factors = []

        # Late attendance factor
        late_count = sum(1 for a in attendance_history if a.get("status") == "late")
        total_days = len(attendance_history) or 1
        late_ratio = late_count / total_days

        if late_ratio > 0.15:
            risk_score += 20
            factors.append("تأخر متكرر (>15% من الأيام)")
        elif late_ratio > 0.05:
            risk_score += 10
            factors.append("تأخر متقطع")
        else:
            risk_score += 5

        # Absenteeism factor
        absent_count = sum(1 for a in attendance_history if a.get("status") == "absent")
        absent_ratio = absent_count / total_days

        if absent_ratio > 0.1:
            risk_score += 25
            factors.append("غياب متكرر (>10%)")
        elif absent_ratio > 0.05:
            risk_score += 15
            factors.append("غياب متقطع")

        # Service years factor
        years_of_service = employee_data.get("years_of_service", 0)
        if years_of_service < 1:
            risk_score += 15
            factors.append("سنة أولى (مرحلة تهيئة)")
        elif years_of_service < 2:
            risk_score += 10
            factors.append("سنتان أوليتان")

        # Tenure factor (longer tenure = lower risk)
        if years_of_service > 5:
            risk_score -= 10
            factors.append("ال전대 طويلة - استقرار عالي")

        # Normalize to 0-100
        risk_score = min(100, max(0, risk_score))

        # Determine risk level
        if risk_score >= 70:
            risk_level = "high"
        elif risk_score >= 40:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "factors": factors,
            "predicted_action": "review" if risk_level == "high" else "monitor",
            "timeframe": "90 days",
            "confidence": "medium",
        }

    def predict_payroll_cost(
        self,
        current_month_cost: float,
        employee_count: int,
        growth_rate: float = 0.02,
        months_ahead: int = 3,
    ) -> Dict[str, Any]:
        """
        Predict future payroll costs based on current trends.
        """
        predictions = []
        current_cost = current_month_cost

        for month in range(1, months_ahead + 1):
            projected = current_cost * ((1 + growth_rate) ** month)
            predictions.append({
                "month": month,
                "projected_cost": round(projected, 2),
                "increase": round(projected - current_cost, 2),
                "increase_percent": round(((projected - current_cost) / current_cost) * 100, 2) if current_cost > 0 else 0,
            })

        return {
            "current_month": current_month_cost,
            "employee_count": employee_count,
            "growth_rate": growth_rate,
            "predictions": predictions,
            "total_increase": round(predictions[-1]["increase"], 2) if predictions else 0,
        }

    def analyze_cv_sentiment(
        self,
        cv_text: str,
    ) -> Dict[str, Any]:
        """
        Analyze the sentiment and tone of a CV.
        Returns indicators about candidate's attitude and communication style.
        """
        # Simple keyword-based analysis
        positive_keywords = [
            "متميز", "مبدع", "متحمس", "متفاني", "مسؤول", "فاعل",
            "قائد", "فريق", "تعاون", "إنجاز", "نجاح", "تقدم",
            "تطوير", "ابتكار", "حل", "تحدي", "تعلم", "نمو",
        ]
        negative_keywords = [
            "صعب", "تحدي كبير", "فشل", "عدم قدرة", "مشكلة جادة",
        ]

        text_lower = cv_text.lower() if cv_text else ""
        positive_count = sum(1 for kw in positive_keywords if kw in text_lower)
        negative_count = sum(1 for kw in negative_keywords if kw in text_lower)

        word_count = len(text_lower.split()) if text_lower else 0

        return {
            "positive_indicators": positive_count,
            "negative_indicators": negative_count,
            "word_count": word_count,
            "communication_quality": "good" if word_count > 100 else "needs_improvement",
            "enthusiasm_indicator": "high" if positive_count > 5 else "medium" if positive_count > 2 else "low",
            "risk_indicators": negative_count,
        }


# Global LLM service instance
llm_service = LLMService()