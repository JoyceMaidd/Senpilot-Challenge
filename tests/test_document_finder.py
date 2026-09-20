from uarb_agent.document_finder import parse_row


def leaf(text, x, y):
    return {"text": text, "x": x, "y": y}


def test_other_documents_row():
    d = parse_row([
        leaf("102674", 14, 350), leaf("Board Order", 130, 350), leaf("07/08/2026", 1394, 350),
        leaf("Public", 14, 385), leaf("Preview", 1442, 386), leaf("GO GET IT", 1311, 386), leaf(".pdf", 1291, 352),
    ], "Other Documents")
    assert d.model_dump() == {
        "doc_no": "102674", "title": "Board Order", "extension": ".pdf", "date": "07/08/2026",
        "security": "Public", "download_reference": "Other Documents:102674",
    }


def test_exhibits_row_with_different_cell_order_and_confidential():
    d = parse_row([
        leaf("HRWC (Board) RIR-1 to RIR-25 CONFIDENTIAL", 123, 620), leaf("05/22/2025", 1395, 620),
        leaf("Confidential", 14, 657), leaf("H-4(C)", 14, 626), leaf("Preview", 1412, 660),
        leaf("GO GET IT", 1308, 660), leaf(".pdf", 1295, 622),
    ], "Exhibits")
    assert (d.doc_no, d.security, d.title, d.download_reference) == (
        "H-4(C)", "Confidential", "HRWC (Board) RIR-1 to RIR-25 CONFIDENTIAL", "Exhibits:H-4(C)")


def test_duplicate_overlapping_elements_ignored():
    d = parse_row([
        leaf("97289", 14, 350), leaf("97289", 14, 350), leaf("Notice", 144, 350), leaf("Public", 14, 385),
        leaf("04/11/2025", 1373, 350), leaf(".pdf", 1284, 352), leaf("GO GET IT", 1298, 387),
    ], "Key Documents")
    assert d.doc_no == "97289" and d.security == "Public" and d.title == "Notice"


def test_non_document_row_is_none():
    assert parse_row([leaf("GO GET IT", 1, 1)], "Exhibits") is None
