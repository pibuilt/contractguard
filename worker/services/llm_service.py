import os
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)


class LLMService:
    def generate(self, prompt: str, max_tokens: int = 120) -> str:
        print("🔥 Calling OpenRouter FREE LLM...")

        try:
            response = client.chat.completions.create(
                model="openrouter/free",  # 🔥 THIS IS THE KEY
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.3
            )
        except Exception as e:
            print("🔥 LLM ERROR:", str(e))
            raise

        generated_text = response.choices[0].message.content

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


llm_service = LLMService()


def build_prompt(clause_text: str, risk_type: str) -> str:
    return f"""
Explain why this contract clause is risky.

Clause:
{clause_text}

Risk Type:
{risk_type}

Answer in 2-3 clear sentences.
"""