import time
import os
from openai import OpenAI
import logging
import re
import random 

logger = logging.getLogger(__name__)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# -------------------------------
# Regex Extraction Helpers
# -------------------------------

def extract_field(text: str, field: str):
    pattern = rf'"{field}"\s*:\s*"([^"]+)"'
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def extract_float(text: str, field: str):
    pattern = rf'"{field}"\s*:\s*([0-9.]+)'
    match = re.search(pattern, text)
    return float(match.group(1)) if match else None


def parse_llm_output(raw: str):
    # remove markdown blocks
    raw = raw.replace("```json", "").replace("```", "").strip()

    return {
        "risk_type": extract_field(raw, "risk_type") or "Unknown",
        "confidence": extract_float(raw, "confidence") or 0.3,
        "why_risky": extract_field(raw, "why_risky") or raw[:200],
        "impact": extract_field(raw, "impact") or "",
        "recommendation": extract_field(raw, "recommendation") or "",
    }


# -------------------------------
# LLM Service
# -------------------------------

class LLMService:

    # -------------------------------
    # CORE CALL (with retry + throttle)
    # -------------------------------

    def _call_llm(self, messages, max_tokens, temperature):

        max_retries = 5
        base_delay = 2  # seconds
        max_delay = 20  # cap

        for attempt in range(max_retries):
            try:
                time.sleep(2)  # base throttle

                response = client.chat.completions.create(
                    model="openrouter/free",
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )

                content = response.choices[0].message.content
                return content or ""

            except Exception as e:
                error_str = str(e)

                if "429" in error_str:
                    # exponential backoff + jitter
                    backoff = min(max_delay, base_delay * (2 ** attempt))
                    jitter = random.uniform(0, 1.5)

                    sleep_time = backoff + jitter

                    logger.warning(
                        f"Rate limited (attempt {attempt+1}/{max_retries}). "
                        f"Sleeping {sleep_time:.2f}s before retry..."
                    )

                    time.sleep(sleep_time)

                else:
                    logger.error(f"LLM call failed: {error_str}", exc_info=True)
                    raise

        raise Exception("LLM failed after retries")

    # -------------------------------
    # TEXT GENERATION (explanations)
    # -------------------------------
    def generate(self, prompt: str, max_tokens: int = 120) -> str:
        print("🔥 Calling OpenRouter FREE LLM...")

        content = self._call_llm(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3
        )

        generated_text = content or ""

        # CLEAN OUTPUT
        lines = generated_text.split("\n")

        cleaned_lines = []
        for line in lines:
            line = line.strip()

            if not line:
                continue

            if any(keyword in line.lower() for keyword in [
                "clause:",
                "risk type:",
                "you are",
                "analyze",
                "answer in",
                "only return",
                "example:"
            ]):
                continue

            cleaned_lines.append(line)

        final_text = " ".join(cleaned_lines)

        if final_text:
            sentences = [s.strip() for s in final_text.split(".") if s.strip()]
            final_text = ". ".join(sentences[:3]) + "."

        return final_text[:400].strip()

    # -------------------------------
    # STRUCTURED ANALYSIS
    # -------------------------------
    def analyze_clause(self, clause_text: str) -> dict:
        prompt = f"""
You are a legal risk analysis system.

Analyze the clause and return ONLY valid JSON.

Clause:
\"\"\"{clause_text}\"\"\"

Return:
{{
"risk_type": "string",
"confidence": 0.0,
"why_risky": "string",
"impact": "string",
"recommendation": "string"
}}

Rules:
- No text outside JSON
- No markdown
- Keep answers short
"""

        try:
            raw = self._call_llm(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.2
            )

            raw = raw.strip()
            if not raw:
                logger.warning("Empty LLM response")
                return None

            logger.warning(f"LLM RAW OUTPUT:\n{raw}")

            parsed = parse_llm_output(raw)

            if not parsed["risk_type"]:
                parsed["risk_type"] = "Unknown"

            return {
                "risk_type": parsed["risk_type"],
                "confidence": float(parsed["confidence"]),
                "why_risky": parsed["why_risky"],
                "impact": parsed["impact"],
                "recommendation": parsed["recommendation"]
            }

        except Exception as e:
            logger.error(f"llm_analysis_failed error={str(e)}", exc_info=True)

            return {
                "risk_type": "Unknown",
                "confidence": 0.3,
                "why_risky": "LLM failed to analyze.",
                "impact": "Potential risk.",
                "recommendation": "Manual review required."
            }


llm_service = LLMService()


# -------------------------------
# Explanation Prompt
# -------------------------------

def build_prompt(clause_text: str, risk_type: str) -> str:
    return f"""
Explain why this contract clause is risky.

Clause:
{clause_text}

Risk Type:
{risk_type}

Answer in 2-3 clear sentences.
"""