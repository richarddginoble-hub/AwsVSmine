from pathlib import Path
import os, requests, json, time, traceback

# Config
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
AUTH_USERS_ENV = os.environ.get('AUTH_USERS', '')  # comma-separated numeric IDs
AUTH_USERS = set(int(x) for x in AUTH_USERS_ENV.split(',') if x.strip())
OWNER = 'richarddginoble-hub'
REPO = 'AwsVSmine'
OFFSET_FILE = Path('telegram_offset.json')
POLL_LIMIT = 50  # Telegram getUpdates limit


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


def run_perform_task():
    # import perform_task from app.py and run it
    try:
        from app import perform_task
    except Exception as e:
        print('Error importing perform_task:', e)
        return False, str(e)
    try:
        perform_task()
        return True, 'OK'
    except Exception as e:
        tb = traceback.format_exc()
        print('perform_task raised:', tb)
        return False, str(e)


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
        # command parsing (only /run supported)
        if text.split()[0] == '/run':
            print('Triggering perform_task()')
            ok, info = run_perform_task()
            print('perform_task result:', ok, info)
            # Optionally, reply to user via Telegram sendMessage (not required)
            if user_id:
                reply_text = 'Triggered' if ok else f'Failed: {info}'
                try:
                    requests.post(f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
                                  json={'chat_id': user_id, 'text': reply_text}, timeout=10)
                except Exception as e:
                    print('Failed to send reply:', e)
    # persist offset so we don't reprocess
    if max_update_id > offset:
        print('Saving new offset', max_update_id)
        save_offset(max_update_id)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
