import os
from openai import OpenAI
import logging
import re

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
    # remove markdown if present
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

    def generate(self, prompt: str, max_tokens: int = 120) -> str:
        print("🔥 Calling OpenRouter FREE LLM...")

        try:
            response = client.chat.completions.create(
                model="openrouter/free",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.3
            )
        except Exception as e:
            print("🔥 LLM ERROR:", str(e))
            raise

        generated_text = response.choices[0].message.content or ""

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

        if len(final_text) > 0:
            sentences = final_text.split(".")
            sentences = [s.strip() for s in sentences if s.strip()]
            final_text = ". ".join(sentences[:3]) + "."

        return final_text[:400].strip()

    # -------------------------------
    # Structured Analysis (REGEX BASED)
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
            response = client.chat.completions.create(
                model="openrouter/free",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.2
            )

            content = response.choices[0].message.content or ""
            raw = content.strip()

            print("LLM RAW OUTPUT:", raw)

            # REGEX PARSING (robust against bad JSON)
            parsed = parse_llm_output(raw)

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
# Explanation Prompt (USED ELSEWHERE)
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