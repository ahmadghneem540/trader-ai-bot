from google import genai
from app.core.config.settings import settings
from app.core.logging.logger import get_logger
from typing import Dict, Any, List
import asyncio
import json

logger = get_logger(__name__)


class AIService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self._client = None
        self._model_name = "gemini-2.0-flash"
        if self.api_key:
            self._client = genai.Client(api_key=self.api_key)

    def _generate_text(self, prompt: str) -> str:
        if not self._client:
            raise ValueError("AI client not initialized properly")

        response = self._client.models.generate_content(
            model=self._model_name,
            contents=prompt,
        )
        return response.text or ""

    async def test_connection(self) -> Dict[str, Any]:
        if not self.api_key:
            logger.error("GEMINI_API_KEY is not set in environment variables")
            raise ValueError("GEMINI_API_KEY is not configured")

        prompt = """Reply with JSON only: 
{ 
  "status":"connected", 
  "message":"Gemini API is working" 
}"""

        try:
            logger.info("Sending test prompt to Gemini API")
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._generate_text(prompt)
            )
            logger.info("Received response from Gemini API")
            return {"response": response}
        except Exception as e:
            logger.exception(f"Error communicating with Gemini API: {str(e)}")
            raise

    async def analyze_candles(self, symbol: str, timeframe: str, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.api_key:
            logger.error("GEMINI_API_KEY is not set in environment variables")
            raise ValueError("GEMINI_API_KEY is not configured")

        prompt = f"""You are a professional institutional trader.

Analyze these candles only.
Symbol: {symbol}
Timeframe: {timeframe}
Candles: {json.dumps(candles, default=str)}

Return JSON only.
Do not explain anything.

Required format:
{{
  "trend": "bullish" or "bearish" or "neutral",
  "confidence": 0.0 to 1.0,
  "reason": "brief explanation",
  "support": [list of support prices],
  "resistance": [list of resistance prices]
}}
"""

        try:
            logger.info(f"Sending candle analysis request to Gemini API for {symbol} {timeframe}")
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._generate_text(prompt)
            )
            logger.info("Received analysis response from Gemini API")
            
            # Try to parse the JSON response
            response_text = response
            # Clean up any markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            parsed_response = json.loads(response_text.strip())
            return parsed_response
        except json.JSONDecodeError as e:
            logger.exception(f"Failed to parse Gemini response as JSON: {str(e)}, response: {response_text}")
            raise ValueError("Invalid JSON response from AI service")
        except Exception as e:
            logger.exception(f"Error communicating with Gemini API: {str(e)}")
            raise


ai_service = AIService()
