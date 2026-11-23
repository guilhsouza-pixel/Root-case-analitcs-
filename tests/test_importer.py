from io import BytesIO

import pandas as pd

from core.importer import detect_kind, list_sheets, load_uploaded


class Uploaded:
    def __init__(self, name: str, raw: bytes):
        self.name = name
        self._raw = raw

    def getvalue(self):
        return self._raw


def make_xlsx() -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame({"Fornecedor": ["A", "B"], "Custo": [10, 20]}).to_excel(
            writer, sheet_name="Dados", index=False
        )
        pd.DataFrame({"Outro": [1]}).to_excel(writer, sheet_name="Resumo", index=False)
    return buffer.getvalue()


def test_xlsx_normal_and_sheets():
    uploaded = Uploaded("base.xlsx", make_xlsx())
    assert detect_kind(uploaded) == "xlsx"
    assert list_sheets(uploaded) == ["Dados", "Resumo"]
    frame = load_uploaded(uploaded, "Dados")
    assert frame.shape == (2, 2)
    assert frame["Custo"].sum() == 30


def test_xlsx_renamed_as_xls_is_detected_by_content():
    uploaded = Uploaded("exportacao.xls", make_xlsx())
    assert detect_kind(uploaded) == "xlsx"
    frame = load_uploaded(uploaded, "Dados")
    assert list(frame["Fornecedor"]) == ["A", "B"]


def test_cp1252_csv_import():
    raw = "Fornecedor;Descrição;Custo\nMegatech;Peça coluna;1234,50\n".encode("cp1252")
    uploaded = Uploaded("base.csv", raw)
    frame = load_uploaded(uploaded)
    assert frame.iloc[0]["Fornecedor"] == "Megatech"
    assert "Descrição" in frame.columns


def test_html_export_disguised_as_xls():
    raw = b"""<html><body><table>
    <tr><th>Fornecedor</th><th>QTD</th></tr>
    <tr><td>Megatech</td><td>28</td></tr>
    </table></body></html>"""
    uploaded = Uploaded("relatorio.xls", raw)
    assert detect_kind(uploaded) == "html"
    frame = load_uploaded(uploaded, "Tabela 1")
    assert frame.iloc[0]["Fornecedor"] == "Megatech"
    assert int(frame.iloc[0]["QTD"]) == 28


def test_duplicate_column_names_are_made_unique():
    raw = b"A;A\n1;2\n"
    uploaded = Uploaded("duplicadas.csv", raw)
    frame = load_uploaded(uploaded)
    assert len(set(frame.columns)) == len(frame.columns)
