from flask import Flask, jsonify, request, abort
import time
import os

app = Flask(__name__)


def perform_task():
    ts = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
    print(f"[TASK] running at {ts}")
    # Example: write to local file if a volume is mounted (not durable on Railway)
    if os.path.isdir('/data'):
        try:
            with open('/data/run.log', 'a') as f:
                f.write(ts + "\n")
        except Exception as e:
            print(f"Failed to write to /data: {e}")


@app.route('/')
def index():
    return jsonify(status="ok")


@app.route('/run', methods=['POST', 'GET'])
def run_once():
    # Optional lightweight protection: compare X-Run-Key header to RUN_KEY env var
    run_key = os.environ.get('RUN_KEY')
    header = request.headers.get('X-Run-Key')
    if run_key:
        if header != run_key:
            abort(403)
    perform_task()
    return jsonify(ran=True)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
