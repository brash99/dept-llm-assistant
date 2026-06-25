#!/usr/bin/env python3
"""
test_llm.py

Simple connectivity test for the departmental LLM server.

This script verifies that:

1. The OpenAI-compatible API is reachable.
2. The configured model exists.
3. A prompt can be submitted.
4. The server returns a response.

Usage:
    python3 scripts/test_llm.py
"""

from openai import OpenAI
from openai import APIConnectionError, APIStatusError

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

BASE_URL = "http://localhost:8000/v1"
MODEL = "qwen3-32b-local"

SYSTEM_PROMPT = (
    "Answer directly and concisely. "
    "Do not include your reasoning in the final response."
)

USER_PROMPT = (
    "In one sentence, explain retrieval augmented generation. "
    "/no_think"
)

MAX_TOKENS = 1000

# ----------------------------------------------------------------------
# Client
# ----------------------------------------------------------------------

client = OpenAI(
    base_url=BASE_URL,
    api_key="not-needed",
)


# ----------------------------------------------------------------------
# Query Function
# ----------------------------------------------------------------------

def query(prompt, system_prompt=SYSTEM_PROMPT):
    """Send a prompt to the configured LLM."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        max_tokens=MAX_TOKENS,
    )

    return response


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main():

    print("=" * 70)
    print("Department LLM Connectivity Test")
    print("=" * 70)

    print(f"Server : {BASE_URL}")
    print(f"Model  : {MODEL}")
    print()

    try:
        response = query(USER_PROMPT)

    except APIConnectionError as exc:
        print("ERROR: Unable to connect to the LLM server.")
        print(exc)
        return

    except APIStatusError as exc:
        print("ERROR: Server returned an API error.")
        print(exc)
        return

    except Exception as exc:
        print("Unexpected error:")
        print(exc)
        return

    message = response.choices[0].message

    print("-" * 70)
    print("FINAL RESPONSE")
    print("-" * 70)

    if message.content:
        print(message.content.strip())
    else:
        print("<No final response returned>")

    reasoning = getattr(message, "reasoning", None)

    if reasoning:
        print()
        print("-" * 70)
        print("REASONING (Debug)")
        print("-" * 70)
        print(reasoning.strip())

    print()
    print("-" * 70)
    print("USAGE")
    print("-" * 70)

    usage = response.usage

    print(f"Prompt tokens     : {usage.prompt_tokens}")
    print(f"Completion tokens : {usage.completion_tokens}")
    print(f"Total tokens      : {usage.total_tokens}")

    print()
    print("✓ Test completed successfully.")


if __name__ == "__main__":
    main()
