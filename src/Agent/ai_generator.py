import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2"


def generate_answer(prompt, max_tokens=150):
    """
    Sends a prompt to the local Ollama model and returns the generated text.
    Runs entirely on your machine — no API key, no cost, no data sent
    anywhere external.
    """
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens
                }
            },
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        return data.get("response", "").strip()

    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to Ollama. Is it running? Try 'ollama serve' in a terminal.")
        return None
    except Exception as e:
        print(f"ERROR generating answer: {e}")
        return None


if __name__ == "__main__":
    test_prompt = "Write one sentence explaining what a Senior Product Designer does."
    result = generate_answer(test_prompt)
    print(f"\nGenerated: {result}")