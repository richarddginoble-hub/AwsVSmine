import time

def perform_task():
    """Test perform_task used by the Telegram poller.

    This is a safe, no-op implementation that logs a timestamp so the Actions
    workflow and poller can run end-to-end during testing.
    """
    ts = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
    print(f"perform_task: test run at {ts}")

if __name__ == '__main__':
    perform_task()
