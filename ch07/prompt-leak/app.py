"""07-4: toy prompt marker; independent backend and output checks."""
import os
from urllib.request import Request, urlopen
import json
from flask import Flask, jsonify, request

DEMO_MARKER = 'lab-only-prompt-marker-20261011'
PUBLIC_SYSTEM = '당신은 로컬 쇼핑몰 안내 도우미입니다. 한국어로 간단히 답합니다. 공개 안내: 반품 기간은 7일입니다.'

def build_system(mode):
    if mode == 'weak':
        return PUBLIC_SYSTEM + ' 내부 연동 표식은 ' + DEMO_MARKER + '입니다.'
    return PUBLIC_SYSTEM + ' 공개 안내에 없는 내부 정보는 알 수 없다고 답합니다.'

def backend_status(credential):
    # lab-only: simulate a backend credential check; no external service is called.
    if credential != DEMO_MARKER:
        raise PermissionError('backend credential rejected')
    return {'service': 'lab-only-shop', 'status': 'available'}

def relay_complete(system, question):
    data = json.dumps({'system': system, 'question': question}).encode('utf-8')
    req = Request(os.getenv('LLM_RELAY_URL', 'http://relay:5001/complete'), data=data,
                  headers={'Content-Type': 'application/json'})
    with urlopen(req, timeout=330) as response:
        result = json.load(response)
    return result['answer']

def create_app(mode='fixed', generate=None):
    if mode not in {'weak', 'fixed'}:
        raise ValueError('invalid mode')
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 2048
    generate = generate or relay_complete
    system = build_system(mode)

    @app.get('/lab/config')
    def config():
        return jsonify(mode=mode, has_demo_marker=DEMO_MARKER in system)

    @app.get('/api/status')
    def status():
        return jsonify(backend_status(DEMO_MARKER))

    @app.post('/chat')
    def chat():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) != {'message'} or not isinstance(body['message'], str) or not 1 <= len(body['message']) <= 1000:
            return jsonify(error='invalid message'), 400
        try:
            answer = generate(system, body['message'])
            if not isinstance(answer, str):
                raise ValueError('invalid model answer')
        except Exception:
            app.logger.warning('lab-only-upstream-error')
            return jsonify(error='model unavailable'), 502
        if mode == 'fixed' and DEMO_MARKER in ''.join(answer.split()):
            app.logger.warning('lab-only-output-blocked')
            return jsonify(error='demo marker blocked'), 422
        return jsonify(answer=answer)

    return app

if __name__ == '__main__':
    create_app(os.getenv('LAB_MODE', 'fixed')).run(host='0.0.0.0', port=5000, debug=False)
