from pathlib import Path
import os, requests, json, time, traceback
import io
import contextlib

# Config
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
AUTH_USERS_ENV = os.environ.get('AUTH_USERS', '')  # comma-separated numeric IDs
AUTH_USERS = set(int(x) for x in AUTH_USERS_ENV.split(',') if x.strip())
OWNER = 'richarddginoble-hub'
REPO = 'AwsVSmine'
OFFSET_FILE = Path('telegram_offset.json')
PENDING_FILE = Path('pending_confirmations.json')
POLL_LIMIT = 50  # Telegram getUpdates limit
RUN_OUTPUT_FILE = Path('run_output.json')
RUN_LOGS_DIR = Path('run_logs')
CONFIRM_TIMEOUT = int(os.environ.get('CONFIRM_TIMEOUT', '600'))  # seconds
REQUIRE_CONFIRMATION = os.environ.get('REQUIRE_CONFIRMATION', 'true').lower() in ('1','true','yes')

# Action environment (available when running in GitHub Actions)
GITHUB_RUN_ID = os.environ.get('GITHUB_RUN_ID')
GITHUB_REPOSITORY = os.environ.get('GITHUB_REPOSITORY')
GITHUB_SERVER_URL = os.environ.get('GITHUB_SERVER_URL', 'https://github.com')

RUN_LOGS_DIR.mkdir(exist_ok=True)


def load_json_file(p, default):
    try:
        return json.loads(p.read_text())
    except Exception:
        return default


def save_json_file(p, data):
    try:
        p.write_text(json.dumps(data, indent=2))
    except Exception as e:
        print(f'Error saving {p}:', e)


def load_offset():
    try:
        data = json.loads(OFFSET_FILE.read_text())
        return int(data.get('offset', 0))
    except Exception:
        return 0


def save_offset(offset):
    OFFSET_FILE.write_text(json.dumps({'offset': offset}))


def telegram_get_updates(offset):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates'
    params = {'offset': offset, 'limit': POLL_LIMIT, 'timeout': 0}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json().get('result', [])


def send_telegram_message(chat_id, text):
    try:
        requests.post(f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
                      json={'chat_id': chat_id, 'text': text}, timeout=10)
    except Exception as e:
        print('Failed to send reply:', e)


def run_perform_task_capture():
    # import perform_task from app.py and run it, capturing stdout/stderr
    try:
        from app import perform_task
    except Exception as e:
        msg = f'Error importing perform_task: {e}'
        print(msg)
        return False, msg, ''
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            perform_task()
        out = buf.getvalue()
        return True, 'OK', out
    except Exception as e:
        tb = traceback.format_exc()
        print('perform_task raised:', tb)
        out = buf.getvalue() + '\n' + tb
        return False, tb, out


def construct_run_url():
    if GITHUB_RUN_ID and GITHUB_REPOSITORY:
        return f"{GITHUB_SERVER_URL}/{GITHUB_REPOSITORY}/actions/runs/{GITHUB_RUN_ID}"
    return None


def add_pending(user_id, username, message_text):
    pend = load_json_file(PENDING_FILE, [])
    ts = int(time.time())
    entry = {'user_id': user_id, 'username': username, 'ts': ts, 'text': message_text}
    pend.append(entry)
    save_json_file(PENDING_FILE, pend)
    return entry


def pop_pending_for_user(user_id):
    pend = load_json_file(PENDING_FILE, [])
    now = int(time.time())
    matches = [p for p in pend if p.get('user_id') == user_id and (now - p.get('ts',0)) <= CONFIRM_TIMEOUT]
    if not matches:
        return None
    # remove the matched entries (all for this user)
    remaining = [p for p in pend if p.get('user_id') != user_id]
    save_json_file(PENDING_FILE, remaining)
    return matches[0]


def write_run_output(user_id, username, ok, info, logs=''):
    try:
        ts = int(time.time())
        content = {
            'timestamp': ts,
            'user_id': user_id,
            'username': username,
            'ok': ok,
            'info': str(info)
        }
        RUN_OUTPUT_FILE.write_text(json.dumps(content, indent=2))
        # write detailed logs
        fname = RUN_LOGS_DIR / f'run_{ts}.log'
        fname.write_text(logs or '')
        return fname.name
    except Exception as e:
        print('Failed to write run output/logs:', e)
        return None


def main():
    if not TELEGRAM_TOKEN:
        print('TELEGRAM_TOKEN not set. Exiting.')
        return 1
    offset = load_offset()
    print('Starting poll loop. offset=', offset)
    updates = telegram_get_updates(offset + 1)
    if not updates:
        print('No new updates.')
        return 0
    max_update_id = offset
    for upd in updates:
        uid = upd.get('update_id')
        if uid and uid > max_update_id:
            max_update_id = uid
        msg = upd.get('message') or upd.get('edited_message') or {}
        if not msg:
            continue
        text = msg.get('text','').strip()
        from_user = msg.get('from', {})
        user_id = from_user.get('id')
        username = from_user.get('username','')
        print(f'Got message from {username} ({user_id}): {text}')
        # authorize
        if AUTH_USERS and (user_id not in AUTH_USERS):
            print('User not authorized:', user_id)
            continue
        cmd = text.split()[0]
        if cmd == '/status':
            # report pending and last run
            pend = load_json_file(PENDING_FILE, [])
            last_run = load_json_file(RUN_OUTPUT_FILE, {})
            reply = f'Pending confirmations: {len([p for p in pend if int(time.time())-p.get("ts",0)<=CONFIRM_TIMEOUT])}\nLast run: {last_run.get("ok")}'
            send_telegram_message(user_id, reply)
            continue
        # confirmation flow
        if cmd == '/run':
            if REQUIRE_CONFIRMATION:
                entry = add_pending(user_id, username, text)
                reply = f'Request queued. Please confirm within {CONFIRM_TIMEOUT//60} minutes by sending /confirm.'
                send_telegram_message(user_id, reply)
                print('Added pending confirmation for', user_id)
                continue
            # otherwise run immediately
            ok, info, logs = run_perform_task_capture()
            logname = write_run_output(user_id, username, ok, info, logs)
            run_url = construct_run_url()
            if run_url:
                reply_text = ('Triggered. Actions run: ' + run_url) if ok else (f'Failed. Actions run: {run_url}\n{info}')
            else:
                reply_text = 'Triggered' if ok else f'Failed: {info}'
            send_telegram_message(user_id, reply_text)
            continue
        if cmd == '/confirm':
            pending = pop_pending_for_user(user_id)
            if not pending:
                send_telegram_message(user_id, 'No pending request found or it expired.')
                print('No pending for', user_id)
                continue
            # execute the pending run
            ok, info, logs = run_perform_task_capture()
            logname = write_run_output(user_id, username, ok, info, logs)
            run_url = construct_run_url()
            if run_url:
                reply_text = ('Confirmed and triggered. Actions run: ' + run_url) if ok else (f'Confirmed but failed. Actions run: {run_url}\n{info}')
            else:
                reply_text = 'Confirmed and triggered' if ok else f'Confirmed but failed: {info}'
            send_telegram_message(user_id, reply_text)
            continue
    # persist offset so we don't reprocess
    if max_update_id > offset:
        print('Saving new offset', max_update_id)
        save_offset(max_update_id)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
