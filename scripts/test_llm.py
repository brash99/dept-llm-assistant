from openai import OpenAI

BASE_URL = "http://localhost:8000/v1"
MODEL = "qwen3-32b-local"

client = OpenAI(
    base_url=BASE_URL,
    api_key="not-needed",
)

print("Connecting to LLM server...")
print(f"Base URL: {BASE_URL}")
print(f"Model:    {MODEL}")
print()

response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {
            "role": "user",
            "content": "In one sentence, explain retrieval augmented generation.",
        }
    ],
    max_tokens=400,
)

message = response.choices[0].message

print("Response:")
print(message.content)

if hasattr(message, "reasoning") and message.reasoning:
    print()
    print("Reasoning field was returned by server.")
