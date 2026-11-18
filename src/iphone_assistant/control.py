"""Cooperative cancellation shared by the UI, audio and execution layers."""
from threading import Event


class RunCanceled(Exception):
    code = 'user_canceled'


def check_stop(stop_event: Event | None) -> None:
    if stop_event is not None and stop_event.is_set():
        raise RunCanceled('User requested stop')
