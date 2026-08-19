import asyncio
import json
import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app as converter_app  # noqa: E402


def test_download_endpoint_selects_document_tables_and_archive(monkeypatch, tmp_path):
    """The query parameter must return the requested generated file."""
    conversion_id = str(uuid.uuid4())
    output_dir = tmp_path / conversion_id
    output_dir.mkdir()
    filenames = {
        "output_filename": f"{conversion_id}.xlsx",
        "tables_filename": f"{conversion_id}_tables.csv",
        "archive_filename": f"{conversion_id}_separate_tables.zip",
    }
    for filename in filenames.values():
        (output_dir / filename).write_bytes(b"test")

    (output_dir / "status.json").write_text(
        json.dumps(
            {
                **filenames,
                "output_mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "tables_mime": "text/csv",
                "archive_mime": "application/zip",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(converter_app, "OUTPUT_FOLDER", str(tmp_path))

    expected = {
        "document": filenames["output_filename"],
        "tables": filenames["tables_filename"],
        "archive": filenames["archive_filename"],
    }
    for kind, filename in expected.items():
        response = asyncio.run(
            converter_app.download_epub(conversion_id, kind=kind, user={"user_id": "test"})
        )
        assert Path(response.path).name == filename
