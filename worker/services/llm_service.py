from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"


class LLMService:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float32
        )

    def generate(self, prompt: str, max_tokens: int = 120) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt")

        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            do_sample=False
        )

        decoded = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # -------------------------------
        # 🔥 CLEAN OUTPUT (IMPORTANT)
        # -------------------------------

        generated_text = decoded[len(prompt):].strip()

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

        # Join lines
        final_text = " ".join(cleaned_lines)

        if len(final_text) > 0:
            sentences = final_text.split(".")
            sentences = [s.strip() for s in sentences if s.strip()]

            # keep only first 2–3 sentences
            final_text = ". ".join(sentences[:3]) + "."

        return final_text[:400].strip()


# Singleton instance (VERY IMPORTANT)
llm_service = LLMService()


# -------------------------------
# Prompt Builder
# -------------------------------
def build_prompt(clause_text: str, risk_type: str) -> str:
    return f"""
You are a legal risk analyst.

Analyze the following clause and explain the risk.

Clause:
{clause_text}

Risk Type:
{risk_type}

Answer in exactly 2-3 sentences explaining:
1. Why this clause is risky
2. What negative consequences may occur

Only return the explanation. Do not include headings, instructions, or the clause itself.
"""