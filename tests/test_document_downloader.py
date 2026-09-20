import pytest

from uarb_agent import document_downloader as dd
from uarb_agent.models import Document, PipelineError


class FakePage:
    def __init__(self, closed=False):
        self._closed = closed

    def is_closed(self):
        return self._closed

    def wait_for_timeout(self, _):
        pass

    def get_by_text(self, *a, **k):  # _close_popup: nothing showing
        class L:
            def count(self): return 0
        return L()


def doc(n):
    return Document(doc_no=str(n), title=f"t{n}", extension=".pdf", date="01/01/2025", security="Public",
                    download_reference=f"Exhibits:{n}")


def test_empty_list_returns_empty_results(tmp_path):
    r = dd.download_documents(FakePage(), "M1", "Exhibits", [], str(tmp_path))
    assert r.downloaded_files == [] and r.failed_downloads == []


def test_closed_page_is_download_failed(tmp_path):
    with pytest.raises(PipelineError) as e:
        dd.download_documents(FakePage(closed=True), "M1", "Exhibits", [doc(1)], str(tmp_path))
    assert e.value.error_code == "DOCUMENT_DOWNLOAD_FAILED"


def test_failed_file_is_retried_three_times_and_does_not_stop_the_rest(tmp_path, monkeypatch):
    calls = {}

    def fake(page, d, dest):
        calls[d.doc_no] = calls.get(d.doc_no, 0) + 1
        if d.doc_no == "2":
            raise RuntimeError("boom")
        return str(tmp_path / f"{d.doc_no}.pdf")

    monkeypatch.setattr(dd, "_download_one", fake)
    r = dd.download_documents(FakePage(), "M1", "Exhibits", [doc(1), doc(2), doc(3)], str(tmp_path))
    assert calls == {"1": 1, "2": 3, "3": 1}
    assert [f.doc_no for f in r.downloaded_files] == ["1", "3"]
    assert [(f.doc_no, f.error) for f in r.failed_downloads] == [("2", "DOWNLOAD_FAILED")]


def test_recovers_when_a_retry_succeeds(tmp_path, monkeypatch):
    n = {"c": 0}

    def flaky(page, d, dest):
        n["c"] += 1
        if n["c"] < 3:
            raise RuntimeError("popup not ready")
        return str(tmp_path / "1.pdf")

    monkeypatch.setattr(dd, "_download_one", flaky)
    r = dd.download_documents(FakePage(), "M1", "Exhibits", [doc(1)], str(tmp_path))
    assert len(r.downloaded_files) == 1 and r.failed_downloads == []
