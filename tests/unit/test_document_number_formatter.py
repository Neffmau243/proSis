from app.services.document import DocumentNumberFormatter


def test_document_number_formatter_includes_site_period_and_padded_sequence() -> None:
    assert DocumentNumberFormatter().format("FUA", 14, "2026", 7) == "FUA-14-2026-00000007"
