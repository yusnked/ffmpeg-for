import sys


def exit_with_interrupt():
    print("\nProcess interrupted by user.")
    sys.exit(130)


def handle_keyboard_interrupt(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            exit_with_interrupt()

    return wrapper
