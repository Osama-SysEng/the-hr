"""
AIsa Client — Connect The H.R to AIsa's APIs, Skills, and LLMs
===============================================================
يستخدم لمكالمة نماذج AIsa، والـ APIs، والـ Skills.

الإعداد:
  export AISA_API_KEY="sk-aisa-CHANGE-ME"

أو ضع المفتاح في ملف .env:
  AISA_API_KEY=sk-aisa-CHANGE-ME
"""

from typing import Any, Dict, List, Optional
import os
import httpx
import json
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# الإعداد
# =============================================================================

AISA_BASE_URL = os.getenv("AISA_BASE_URL", "https://api.aisa.one/v1")
AISA_API_KEY = os.getenv(
    "AISA_API_KEY",
    ""
)
AISA_APIS_BASE_URL = os.getenv("AISA_APIS_BASE_URL", "https://api.aisa.one/apis/v1")

# الحد الأقصى للمكالمات المدفوعة (الحماية)
MAX_COST_USD = float(os.getenv("AISA_MAX_COST_USD", "10.0"))
COST_TRACKER: Dict[str, float] = {"total_spend": 0.0}


# =============================================================================
# العميل
# =============================================================================

class AIsaClient:
    """
    عميل AIsa لمكالمة النماذج والـ APIs ومهارات AIsa.

    يدعم:
    - Chat completions (OpenAI-compatible)
    - Data APIs (non-chat capabilities)
    - Skills (عند توفرها)
    - Model listing and capability discovery
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.api_key = api_key or AISA_API_KEY
        self.base_url = base_url or AISA_BASE_URL
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    def close(self):
        self._client.close()

    # -------------------------------------------------------------------------
    # النماذج (Models)
    # -------------------------------------------------------------------------
    def list_models(self) -> List[Dict[str, Any]]:
        """الحصول على قائمة النماذج المتاحة"""
        response = self._client.get("/models")
        response.raise_for_status()
        data = response.json()
        models = data.get("data", [])
        return models

    def get_model_info(self, model: str) -> Dict[str, Any]:
        """معلومات نموذج محدد"""
        response = self._client.get(f"/models/{model}")
        response.raise_for_status()
        return response.json()

    # -------------------------------------------------------------------------
    # Chat Completions (OpenAI-compatible)
    # -------------------------------------------------------------------------
    def chat_completions(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4000,
        stream: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        إرسال طلب Chat Completion إلى AIsa.

        Args:
            model: اسم النموذج (مثلاً: "gpt-4o-mini" أو نماذج AIsa الخاصة)
            messages: قائمة الرسائل [{role, content}, ...]
            temperature: grado درجة حرارة
            max_tokens: الحد الأقصى للـ tokens
            stream: ما إذا كان التدفق مفعّلًا

        Returns:
            الرد من AIsa
        """
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }
        if stream:
            payload["stream"] = True

        response = self._client.post("/chat/completions", json=payload)

        # تتبع التكلفة (تقديري — يُستبدل بالـ x-aisa-pricing الحقيقي)
        cost_header = response.headers.get("x-aisa-pricing")
        if cost_header:
            try:
                cost = float(cost_header)
                COST_TRACKER["total_spend"] += cost
                if COST_TRACKER["total_spend"] > MAX_COST_USD:
                    raise RuntimeError(
                        f"تخطى الحد الأقصى للتكلفة (${MAX_COST_USD})"
                    )
            except (ValueError, TypeError) as exc:
                # Malformed pricing header — ignore it but keep a trace.
                logger.debug("Ignoring invalid x-aisa-pricing header %r: %s", cost_header, exc)

        response.raise_for_status()
        return response.json()

    def chat_completion_simple(
        self,
        prompt: str,
        model: str = "gpt-4o-mini",
        system: str = "You are a helpful assistant.",
        temperature: float = 0.3,
    ) -> str:
        """
        مكالمة بسيطة: إرسال prompt والحصول على إجابة نصية.
        """
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        result = self.chat_completions(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        content = result["choices"][0]["message"]["content"]
        return content

    # -------------------------------------------------------------------------
    # Data APIs (غير-Chat)
    # -------------------------------------------------------------------------
    def call_api(
        self,
        endpoint: str,
        method: str = "GET",
        payload: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        مكالمة إلى AIsa Data APIs.
        المسار الكامل: https://api.aisa.one/apis/v1/{endpoint}
        """
        url = f"{AISA_APIS_BASE_URL}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        with httpx.Client(timeout=self.timeout) as client:
            if method == "GET":
                response = client.get(url, headers=headers, params=payload)
            elif method == "POST":
                response = client.post(url, headers=headers, json=payload)
            elif method == "PUT":
                response = client.put(url, headers=headers, json=payload)
            elif method == "DELETE":
                response = client.delete(url, headers=headers, params=payload)
            else:
                raise ValueError(f"Method not supported: {method}")

        response.raise_for_status()
        return response.json()

    # -------------------------------------------------------------------------
    # Skills
    # -------------------------------------------------------------------------
    def list_skills(self) -> List[Dict[str, Any]]:
        """الحصول على قائمة مهارات AIsa المتاحة"""
        return self.call_api("skills", method="GET")

    def call_skill(
        self,
        skill_name: str,
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """استدعاء مهارة محددة"""
        return self.call_api(
            f"skills/{skill_name}/execute",
            method="POST",
            payload=input_data,
        )

    # -------------------------------------------------------------------------
    # التكلفة والتتبع
    # -------------------------------------------------------------------------
    def get_cost_tracker(self) -> Dict[str, float]:
        """الحصول على تتبع التكلفة الحالي"""
        return dict(COST_TRACKER)

    def reset_cost_tracker(self):
        """إعادة تعيين تتبع التكلفة"""
        COST_TRACKER["total_spend"] = 0.0


# =============================================================================
# التهيئة السريعة
# =============================================================================

_client: Optional[AIsaClient] = None


def get_aisa_client() -> AIsaClient:
    """الحصول على عميل AIsa مشترك (singleton)"""
    global _client
    if _client is None:
        _client = AIsaClient()
    return _client


def close_aisa_client():
    """إغلاق عميل AIsa"""
    global _client
    if _client:
        _client.close()
        _client = None


# =============================================================================
# استخدام في The H.R
# =============================================================================

# Example: استخدام AIsa للاستخراج من السيرة الذاتية بدلًا من OpenAI
"""
from app.services.aisa_client import get_aisa_client, close_aisa_client

def extract_cv_with_aisa(cv_text: str) -> dict:
    client = get_aisa_client()
    try:
        result = client.chat_completion_simple(
            prompt=f"Extract structured data from this CV:\\n\\n{cv_text}",
            model="gpt-4o-mini",
            system="You are an expert HR recruiter. Extract all relevant information from the CV.",
        )
        return json.loads(result)
    finally:
        close_aisa_client()
"""

# Example: استخدام AIsa Skills للمهام المتخصصة
"""
from app.services.aisa_client import get_aisa_client, close_aisa_client

def use_aisa_skill(skill_name: str, data: dict) -> dict:
    client = get_aisa_client()
    try:
        return client.call_skill(skill_name, data)
    finally:
        close_aisa_client()
"""
