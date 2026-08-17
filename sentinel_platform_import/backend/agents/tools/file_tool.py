from pathlib import Path


class FileTool:

    def create_file(self, path, content):

        file_path = Path(path)

        file_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        if file_path.exists():
            return {
                "status": "failed",
                "action": "create_file",
                "path": str(file_path),
                "error": "file already exists"
            }

        file_path.write_text(
            content,
            encoding="utf-8"
        )

        return {
            "status": "completed",
            "action": "create_file",
            "path": str(file_path)
        }

    def read_file(self, path):

        file_path = Path(path)

        return {
            "status": "completed",
            "action": "read_file",
            "path": str(file_path),
            "content": file_path.read_text(
                encoding="utf-8"
            )
        }
