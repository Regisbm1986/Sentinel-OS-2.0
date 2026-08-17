import subprocess

import pytest

from sentinel_os.platform.backend.agents.tools.command_tool import CommandTool


class FakeCompletedProcess:
    def __init__(self, stdout, stderr, returncode):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def test_command_tool_returns_failed_status_on_nonzero_returncode(monkeypatch):
    fake_result = FakeCompletedProcess(
        stdout="",
        stderr="command not found",
        returncode=127,
    )

    def fake_run(command, shell, capture_output, text):
        assert command == "false"
        assert shell is True
        assert capture_output is True
        assert text is True
        return fake_result

    monkeypatch.setattr(subprocess, "run", fake_run)

    tool = CommandTool()
    result = tool.execute("false")

    assert result["status"] == "failed"
    assert result["command"] == "false"
    assert result["stdout"] == ""
    assert result["stderr"] == "command not found"
    assert result["returncode"] == 127


def test_command_tool_returns_completed_status_on_zero_returncode(monkeypatch):
    fake_result = FakeCompletedProcess(
        stdout="ok",
        stderr="",
        returncode=0,
    )

    def fake_run(command, shell, capture_output, text):
        return fake_result

    monkeypatch.setattr(subprocess, "run", fake_run)

    tool = CommandTool()
    result = tool.execute("echo ok")

    assert result["status"] == "completed"
    assert result["stdout"] == "ok"
    assert result["stderr"] == ""
    assert result["returncode"] == 0
