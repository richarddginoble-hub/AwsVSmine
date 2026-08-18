from telebot import TeleBot
import os, requests, json, time, threading

TG_TOKEN = os.environ.get('TG_TOKEN')
GITHUB_PAT = os.environ.get('GITHUB_PAT')  # optional
OWNER = os.environ.get('REPO_OWNER', 'richarddginoble-hub')
REPO = os.environ.get('REPO_NAME', 'AwsVSmine')
WORKFLOW_FILE = os.environ.get('WORKFLOW_FILE', 'scheduled-task.yml')
REF = os.environ.get('REF', 'main')
AUTH_USERS = set(int(x) for x in os.environ.get('AUTH_USERS','').split(',') if x.strip())

QUEUE_FILE = 'run-requests.json'
LOCK = threading.Lock()

bot = TeleBot(TG_TOKEN)

def save_queue(queue):
    with LOCK:
        with open(QUEUE_FILE, 'w') as f:
            json.dump(queue, f)

def load_queue():
    try:
        with LOCK:
            with open(QUEUE_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        return []

def append_queue(item):
    q = load_queue()
    q.append(item)
    save_queue(q)

def trigger_workflow(inputs=None):
    if not GITHUB_PAT:
        return None, 'no-github-pat'
    url = f'https://api.github.com/repos/{OWNER}/{REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches'
    headers = {
        'Authorization': f'token {GITHUB_PAT}',
        'Accept': 'application/vnd.github+json'
    }
    payload = {'ref': REF}
    if inputs:
        payload['inputs'] = inputs
    r = requests.post(url, json=payload, headers=headers, timeout=15)
    return r.status_code, r.text

@bot.message_handler(commands=['run'])
def on_run(msg):
    if AUTH_USERS and (msg.from_user.id not in AUTH_USERS):
        bot.reply_to(msg, 'Not authorized.')
        return
    if not GITHUB_PAT:
        append_queue({
            'user_id': msg.from_user.id,
            'username': getattr(msg.from_user, 'username', ''),
            'ts': int(time.time())
        })
        bot.reply_to(msg, 'No GitHub token configured. Your run request was queued and will be processed later.')
        return
    bot.reply_to(msg, 'Triggering workflow...')
    code, text = trigger_workflow({'triggered_by': str(msg.from_user.id)})
    if code == 204:
        bot.reply_to(msg, 'Workflow triggered.')
    else:
        bot.reply_to(msg, f'Failed: {code} {text}')

@bot.message_handler(commands=['status'])
def on_status(msg):
    if AUTH_USERS and (msg.from_user.id not in AUTH_USERS):
        bot.reply_to(msg, 'Not authorized.')
        return
    if not GITHUB_PAT:
        q = load_queue()
        bot.reply_to(msg, f'No GitHub token configured. {len(q)} queued requests.')
        return
    url = f'https://api.github.com/repos/{OWNER}/{REPO}/actions/workflows/{WORKFLOW_FILE}/runs?per_page=1'
    headers = {'Authorization': f'token {GITHUB_PAT}'}
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        bot.reply_to(msg, f'API error: {r.status_code}')
        return
    data = r.json()
    if 'workflow_runs' not in data or len(data['workflow_runs'])==0:
        bot.reply_to(msg, 'No runs found')
        return
    run = data['workflow_runs'][0]
    bot.reply_to(msg, f"Status: {run.get('conclusion') or run.get('status')} (run #{run.get('run_number')})")

def process_queue_loop():
    while True:
        if GITHUB_PAT:
            q = load_queue()
            if q:
                for item in list(q):
                    code, text = trigger_workflow({'triggered_by': str(item.get('user_id'))})
                    if code == 204:
                        q = load_queue()
                        q = [it for it in q if not (it.get('user_id')==item.get('user_id') and it.get('ts')==item.get('ts'))]
                        save_queue(q)
        time.sleep(30)

if __name__ == '__main__':
    if not TG_TOKEN:
        print('TG_TOKEN not set. Exiting.')
        exit(1)
    t = threading.Thread(target=process_queue_loop, daemon=True)
    t.start()
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
