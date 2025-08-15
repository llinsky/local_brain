import signal


class Timeout:
    """
    A class to produce an exception if the code block has not completed in the specified seconds.
    """
    def __init__(self, seconds=60, error_message="ABORTING: TIMEOUT ERROR"):
        self.seconds = seconds
        self.error_message = error_message

    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, type, value, traceback):
        signal.alarm(0)
