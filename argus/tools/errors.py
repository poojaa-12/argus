from __future__ import annotations


class ToolError(Exception):
    pass


class ToolTimeoutError(ToolError):
    pass


class MalformedResponseError(ToolError):
    pass


class ExecutorError(ToolError):
    pass


class PermanentToolError(ToolError):
    pass

