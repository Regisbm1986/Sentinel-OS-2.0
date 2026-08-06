from pathlib import Path

from sentinel_os.platform.backend.agents.tools.file_tool import FileTool


def test_file_tool_create_file_fails_if_existing(tmp_path):
    path = tmp_path / "demo.txt"
    path.write_text("existing content", encoding="utf-8")

    tool = FileTool()
    result = tool.create_file(str(path), "new content")

    assert result["status"] == "failed"
    assert result["action"] == "create_file"
    assert result["path"] == str(path)
    assert result["error"] == "file already exists"
    assert path.read_text(encoding="utf-8") == "existing content"


def test_file_tool_create_file_succeeds_when_missing(tmp_path):
    path = tmp_path / "demo.txt"

    tool = FileTool()
    result = tool.create_file(str(path), "new content")

    assert result["status"] == "completed"
    assert path.read_text(encoding="utf-8") == "new content"
