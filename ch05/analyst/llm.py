"""OpenAI-compatible client. Offline commands do not import the SDK."""
import os
from pathlib import Path

def complete(system, payload, schema):
    from dotenv import load_dotenv
    from openai import OpenAI
    load_dotenv(Path(__file__).resolve().parents[2] / '.env')
    base = os.getenv('OPENAI_BASE_URL', 'http://localhost:11434/v1')
    client = OpenAI(base_url=base, api_key=os.getenv('OPENAI_API_KEY', 'lab-only-ollama'), timeout=300, max_retries=0)
    opts = {}
    effort = os.getenv('LLM_REASONING_EFFORT', 'none' if '11434' in base else '')
    if effort:
        opts['reasoning_effort'] = effort
    if '11434' in base:
        opts['temperature'] = 0
    opts['max_tokens' if '11434' in base else 'max_completion_tokens'] = 1600
    try:
        response = client.chat.completions.create(model=os.getenv('OPENAI_MODEL', 'qwen3.5:4b'),
            messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': payload}],
            response_format={'type': 'json_schema', 'json_schema': {'name': 'lab_analysis', 'strict': True, 'schema': schema}}, **opts)
    except Exception as exc:
        raise ValueError('model call failed: ' + type(exc).__name__) from None
    if response.choices[0].finish_reason != 'stop':
        raise ValueError('incomplete model response')
    return response.choices[0].message.content or ''
