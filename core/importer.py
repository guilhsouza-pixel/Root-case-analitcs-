from __future__ import annotations

from io import BytesIO, StringIO
from typing import Any

import pandas as pd


OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
ZIP_MAGIC = b"PK\x03\x04"


class ImportErrorDetail(ValueError):
    """Erro de importação com mensagem adequada para exibição ao usuário."""


def _name(uploaded: Any) -> str:
    return str(getattr(uploaded, "name", "arquivo")).strip() or "arquivo"


def _bytes(uploaded: Any) -> bytes:
    if hasattr(uploaded, "getvalue"):
        raw = uploaded.getvalue()
    elif isinstance(uploaded, (bytes, bytearray)):
        raw = bytes(uploaded)
    else:
        raise ImportErrorDetail("O arquivo recebido não fornece conteúdo binário.")
    if not raw:
        raise ImportErrorDetail("O arquivo está vazio.")
    return raw


def detect_kind(uploaded: Any) -> str:
    """Detecta o formato pelo conteúdo; extensão é apenas fallback."""
    raw = _bytes(uploaded)
    head = raw[:4096].lstrip()
    lower = head.lower()

    if raw.startswith(OLE_MAGIC):
        return "xls"
    if raw.startswith(ZIP_MAGIC):
        return "xlsx"
    if lower.startswith((b"<html", b"<!doctype html")) or b"<table" in lower[:2048]:
        return "html"
    if lower.startswith(b"<?xml") or b"<workbook" in lower[:2048]:
        return "xml"

    name = _name(uploaded).lower()
    if name.endswith(".csv"):
        return "csv"
    if name.endswith(".xlsx"):
        return "xlsx"
    if name.endswith(".xls"):
        # Exportações corporativas podem ser texto/CSV com extensão .xls.
        # Se não houver assinatura binária, tente como texto antes de falhar.
        return "text-xls"
    return "text"


def _read_csv_bytes(raw: bytes) -> pd.DataFrame:
    errors: list[str] = []
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError as exc:
            errors.append(f"{encoding}: {exc}")
            continue
        try:
            return pd.read_csv(StringIO(text), sep=None, engine="python")
        except Exception as exc:  # pragma: no cover - mensagem acumulada
            errors.append(f"{encoding}: {exc}")
    raise ImportErrorDetail(
        "Não foi possível interpretar o arquivo como CSV/texto. "
        + " | ".join(errors[-3:])
    )


def _read_html_bytes(raw: bytes, sheet_name: str | int | None = None) -> pd.DataFrame:
    try:
        tables = pd.read_html(BytesIO(raw))
    except Exception as exc:
        raise ImportErrorDetail(f"Não foi possível interpretar a tabela HTML: {exc}") from exc
    if not tables:
        raise ImportErrorDetail("Nenhuma tabela foi encontrada no arquivo HTML.")
    index = 0
    if isinstance(sheet_name, int):
        index = sheet_name
    if index < 0 or index >= len(tables):
        raise ImportErrorDetail("A tabela selecionada não existe no arquivo.")
    return tables[index]


def list_sheets(uploaded: Any) -> list[str]:
    kind = detect_kind(uploaded)
    raw = _bytes(uploaded)
    try:
        if kind == "xlsx":
            return pd.ExcelFile(BytesIO(raw), engine="openpyxl").sheet_names
        if kind == "xls":
            return pd.ExcelFile(BytesIO(raw), engine="xlrd").sheet_names
        if kind == "html":
            tables = pd.read_html(BytesIO(raw))
            return [f"Tabela {i + 1}" for i in range(len(tables))]
        # SpreadsheetML XML e arquivos texto não têm suporte confiável a múltiplas abas aqui.
        return []
    except Exception as exc:
        raise ImportErrorDetail(
            f"Não foi possível listar as abas de {_name(uploaded)}: {exc}"
        ) from exc


def load_uploaded(uploaded: Any, sheet_name: str | int | None = None) -> pd.DataFrame:
    kind = detect_kind(uploaded)
    raw = _bytes(uploaded)

    try:
        if kind == "xlsx":
            frame = pd.read_excel(
                BytesIO(raw),
                sheet_name=sheet_name if sheet_name is not None else 0,
                engine="openpyxl",
            )
        elif kind == "xls":
            frame = pd.read_excel(
                BytesIO(raw),
                sheet_name=sheet_name if sheet_name is not None else 0,
                engine="xlrd",
            )
        elif kind == "html":
            index = 0
            if isinstance(sheet_name, str) and sheet_name.startswith("Tabela "):
                try:
                    index = int(sheet_name.split()[-1]) - 1
                except ValueError:
                    index = 0
            elif isinstance(sheet_name, int):
                index = sheet_name
            frame = _read_html_bytes(raw, index)
        elif kind == "xml":
            # Tentativa principal para SpreadsheetML/HTML-like exportado como XLS.
            try:
                tables = pd.read_html(BytesIO(raw))
                if tables:
                    frame = tables[0]
                else:
                    raise ValueError("nenhuma tabela")
            except Exception:
                frame = pd.read_xml(BytesIO(raw))
        else:
            frame = _read_csv_bytes(raw)
    except ImportErrorDetail:
        raise
    except Exception as exc:
        raise ImportErrorDetail(
            f"Falha ao ler {_name(uploaded)} (formato detectado: {kind}): {exc}"
        ) from exc

    if isinstance(frame, dict):
        # Segurança caso um leitor seja chamado com sheet_name=None.
        frame = next(iter(frame.values()), pd.DataFrame())

    if frame is None or frame.empty:
        raise ImportErrorDetail("O arquivo foi lido, mas não contém linhas de dados.")

    # Evita nomes de coluna duplicados/NaN que quebram widgets e mapeamento.
    cols: list[str] = []
    seen: dict[str, int] = {}
    for idx, col in enumerate(frame.columns):
        base = str(col).strip()
        if not base or base.lower() == "nan":
            base = f"coluna_{idx + 1}"
        count = seen.get(base, 0)
        seen[base] = count + 1
        cols.append(base if count == 0 else f"{base}_{count + 1}")
    frame.columns = cols

    return frame
