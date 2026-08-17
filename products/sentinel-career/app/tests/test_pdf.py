from __future__ import annotations

import json

from products.sentinel_career.backend.ats.analyzer import analyze_resume
from products.sentinel_career.backend.ats.pdf_reader import extract_text_from_pdf


def _build_pdf_bytes(text: str) -> bytes:
    # Minimal PDF generator to embed the provided text for extraction during tests.
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content_stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET\n".encode("ascii")

    parts = [b"%PDF-1.4\n"]
    offsets = [0]
    obj_id = 1

    def add_obj(body: bytes) -> None:
        nonlocal obj_id
        offset = sum(len(part) for part in parts)
        offsets.append(offset)
        parts.append(f"{obj_id} 0 obj\n".encode("ascii"))
        parts.append(body)
        if not body.endswith(b"\n"):
            parts.append(b"\n")
        parts.append(b"endobj\n")
        obj_id += 1

    add_obj(b"<< /Type /Catalog /Pages 2 0 R >>")
    add_obj(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")

    page_body = (
        b"<< /Type /Page /Parent 2 0 R "
        b"/MediaBox [0 0 612 792] "
        b"/Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>"
    )
    add_obj(page_body)

    stream_body = (
        f"<< /Length {len(content_stream)} >>\n".encode("ascii")
        + b"stream\n"
        + content_stream
        + b"endstream\n"
    )
    add_obj(stream_body)

    add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    xref_offset = sum(len(part) for part in parts)
    parts.append(b"xref\n0 6\n")
    parts.append(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        parts.append(f"{offset:010d} 00000 n \n".encode("ascii"))
    parts.append(b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n")
    parts.append(f"{xref_offset}\n%%EOF".encode("ascii"))

    return b"".join(parts)


def test_pdf_resume_analysis(tmp_path, monkeypatch):
    pdf_bytes = _build_pdf_bytes("Experiencia Sentinel OS em suporte")
    pdf_path = tmp_path / "curriculo.pdf"
    pdf_path.write_bytes(pdf_bytes)

    extracted_text = extract_text_from_pdf(str(pdf_path))
    assert "Experiencia Sentinel OS" in extracted_text

    def _fake_ask_gpt(prompt: str) -> str:
        assert "Experiencia Sentinel OS" in prompt
        return json.dumps(
            {
                "career_health": {"score": 82, "status": "healthy"},
                "recommendations": ["Evidencie resultados mensuráveis"],
            }
        )

    monkeypatch.setattr("products.sentinel_career.backend.ats.analyzer.ask_gpt", _fake_ask_gpt)

    result = analyze_resume(extracted_text)

    assert result["success"] is True
    assert result["error"] is None
    assert "career_health" in result.get("data", {})
    assert result["data"]["career_health"]["score"] == 82
    assert "recommendations" in result.get("data", {})
