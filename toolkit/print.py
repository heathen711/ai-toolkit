import sys
import os
from datetime import datetime
from toolkit.accelerator import get_accelerator


def get_timestamp():
    """Get current timestamp in a readable format."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def print_acc(*args, **kwargs):
    """Print with timestamp prefix, only on main process."""
    if get_accelerator().is_local_main_process:
        timestamp = get_timestamp()
        # If there are args, prefix the first one with timestamp
        if args:
            # Convert first arg to string and add timestamp
            first_arg = f"[{timestamp}] {args[0]}"
            print(first_arg, *args[1:], **kwargs)
        else:
            # No args, just print timestamp
            print(f"[{timestamp}]", **kwargs)


class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, 'a')
        self.at_line_start = True  # Track if we're at the start of a new line

    def write(self, message):
        # Add timestamp to the beginning of each line
        if message and self.at_line_start and message.strip():
            timestamp = get_timestamp()
            timestamped_message = f"[{timestamp}] {message}"
            self.terminal.write(timestamped_message)
            self.log.write(timestamped_message)
        else:
            self.terminal.write(message)
            self.log.write(message)

        # Update line start tracker
        if message:
            self.at_line_start = message.endswith('\n')

        self.log.flush()  # Make sure it's written immediately

    def flush(self):
        self.terminal.flush()
        self.log.flush()


def setup_log_to_file(filename):
    if get_accelerator().is_local_main_process:
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
    sys.stdout = Logger(filename)
    sys.stderr = Logger(filename)
