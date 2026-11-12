"""Run a bounded model-to-Relate recall lookup using a localhost chat server."""

import argparse
import json
import re
from urllib.error import URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

import relate

from recall import trace_batch


TRACE_TOOL = {
    'type': 'function',
    'function': {
        'name': 'trace_batch',
        'description': 'Find the active kit path and loan for the batch named in a recall question.',
        'parameters': {
            'type': 'object',
            'properties': {'batch_id': {'type': 'string'}},
            'required': ['batch_id'],
            'additionalProperties': False,
        },
    },
}
SYSTEM_PROMPT = (
    'For a recall question naming a batch, call trace_batch once with the exact batch ID '
    'whose current location is being requested. Do not guess any inventory facts. '
    'After you receive the tool result, return its exact JSON object, with no other text.'
)


class LocalOnlyRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def chat(messages, model, port, *, select_tool, timeout):
    payload = {
        'model': model,
        'messages': messages,
        'tools': [TRACE_TOOL],
        'tool_choice': 'auto' if select_tool else 'none',
        'temperature': 0,
        'max_tokens': 384,
        'chat_template_kwargs': {'enable_thinking': False},
    }
    request = Request(
        f'http://127.0.0.1:{port}/v1/chat/completions',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
    )
    opener = build_opener(ProxyHandler({}), LocalOnlyRedirects())
    with opener.open(request, timeout=timeout) as response:
        completion = json.load(response)
    return completion['choices'][0]['message']


def run_recall(database, question, model, port, timeout=180):
    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': question},
    ]
    assistant = chat(messages, model, port, select_tool=True, timeout=timeout)
    calls = assistant.get('tool_calls') or []
    if len(calls) != 1 or calls[0]['function']['name'] != 'trace_batch':
        raise ValueError('The model did not request exactly one recall lookup.')

    call = calls[0]
    args = json.loads(call['function']['arguments'])
    if not isinstance(args, dict) or set(args) != {'batch_id'}:
        raise ValueError('The model returned invalid lookup arguments.')
    batch = args['batch_id']
    if not isinstance(batch, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', batch):
        raise ValueError('The model returned an invalid batch ID.')
    batch_token = rf'(?<![A-Za-z0-9_-]){re.escape(batch)}(?![A-Za-z0-9_-])'
    if not re.search(batch_token, question, re.IGNORECASE):
        raise ValueError('The model selected a batch ID absent from the question.')

    with relate.connect(database, read_only=True) as connection:
        result = {'batch': batch, 'matches': trace_batch(connection, batch)}

    messages.extend((
        {'role': 'assistant', 'content': assistant.get('content') or '', 'tool_calls': calls},
        {'role': 'tool', 'tool_call_id': call['id'], 'content': json.dumps(result)},
    ))
    response = chat(messages, model, port, select_tool=False, timeout=timeout)
    try:
        echoed_result = json.loads(response.get('content') or '')
    except json.JSONDecodeError:
        echoed_result = None
    return {**result, 'model_returned_exact_tool_result': echoed_result == result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database')
    parser.add_argument('question')
    parser.add_argument('--model', required=True)
    parser.add_argument('--port', type=int, default=1234)
    parser.add_argument('--timeout', type=int, default=180, help='Seconds to wait per model request.')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('Port must be in 1–65535.')
    if args.timeout < 1:
        parser.error('Timeout must be at least one second.')

    try:
        result = run_recall(args.database, args.question, args.model, args.port, args.timeout)
    except (ValueError, URLError, TimeoutError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
