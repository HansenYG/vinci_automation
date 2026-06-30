"""Excel export for the chatbot ("can export as excel files")."""

from __future__ import annotations

import io
from typing import Any

from openpyxl import Workbook


def rows_to_xlsx(rows: list[dict[str, Any]], sheet_name: str = "Export") -> bytes:
    """Serialise a list of uniform dict rows into an .xlsx byte stream."""
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name[:31] or "Export"

    if rows:
        headers = list({k for row in rows for k in row.keys()})
        ws.append(headers)
        for row in rows:
            ws.append([_stringify(row.get(h)) for h in headers])
    else:
        ws.append(["(no rows)"])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _stringify(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return str(value)
    return value
