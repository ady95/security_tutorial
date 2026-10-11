"""Only this relay receives provider credentials. No shell or tools."""
import os
from urllib.parse import urlsplit, urlunsplit
from flask import Flask, jsonify, request
from openai import OpenAI

def upstream_url():
    base = os.getenv('OPENAI_BASE_URL', 'http://host.docker.internal:11434/v1')
    parsed = urlsplit(base)
    if parsed.hostname in {'localhost', '127.0.0.1'} and parsed.port == 11434:
        parsed = parsed._replace(netloc='host.docker.internal:11434')
    return urlunsplit(parsed)

def create_app():
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 24000
    base = upstream_url()
    client = OpenAI(base_url=base, api_key=os.getenv('OPENAI_API_KEY', 'lab-only-ollama'), timeout=300, max_retries=0)

    @app.post('/complete')
    def complete():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) != {'system', 'question'} or not all(isinstance(body[k], str) for k in body):
            return jsonify(error='invalid request'), 400
        opts = {}
        effort = os.getenv('LLM_REASONING_EFFORT', 'none' if '11434' in base else '')
        if effort:
            opts['reasoning_effort'] = effort
        opts['max_tokens' if '11434' in base else 'max_completion_tokens'] = 1000
        try:
            result = client.chat.completions.create(model=os.getenv('OPENAI_MODEL', 'qwen3.5:4b'),
                messages=[{'role': 'system', 'content': body['system']}, {'role': 'user', 'content': body['question']}], **opts)
            if result.choices[0].finish_reason != 'stop':
                raise ValueError('incomplete response')
            return jsonify(answer=result.choices[0].message.content or '')
        except Exception:
            app.logger.warning('lab-only-provider-error')
            return jsonify(error='provider unavailable'), 502

    return app

if __name__ == '__main__':
    create_app().run(host='0.0.0.0', port=5001, debug=False)
