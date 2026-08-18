from app import perform_task
import os
import time

os.makedirs('run-output', exist_ok=True)

if __name__ == '__main__':
    ts = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
    print(f"[RUN_TASK] starting at {ts}")
    try:
        perform_task()
        with open('run-output/last_run.txt', 'a') as f:
            f.write(ts + "\n")
        print("[RUN_TASK] finished")
    except Exception as e:
        print(f"[RUN_TASK] failed: {e}")
        raise
