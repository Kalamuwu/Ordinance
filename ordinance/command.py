from typing import Callable

def _make_decorator(command_name: str, attrs: dict):
    def decorator(coro):
        if not isinstance(coro, Callable):
            raise Exception()
            #TODO ordinance.exceptions.SchedulerError(f"Cannot schedule non-method {coro}")
        if not hasattr(coro, '__ordinance_commands'):
            coro.__ordinance_commands = {}
        if command_name in coro.__ordinance_commands:
            raise Exception()
            #TODO
        coro.__ordinance_commands[command_name] = attrs
        return coro
    return decorator

def command(command_name: str):
    return _make_decorator(command_name, {})
