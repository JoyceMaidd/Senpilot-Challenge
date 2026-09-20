import zipfile

from uarb_agent.models import DownloadedFile, DownloadResult, FailedDownload
from uarb_agent.zip_tool import make_zip


def _result(tmp_path, names, failed=()):
    files = []
    for n in names:
        p = tmp_path / n
        p.write_bytes(b"data-" + n.encode())
        files.append(DownloadedFile(doc_no=n.split(".")[0], title="t", local_path=str(p)))
    return DownloadResult(
        matter_number="M12205", document_type="Other Documents",
        downloaded_files=files, failed_downloads=list(failed),
    )


def test_multiple_files_and_filename(tmp_path):
    z = make_zip(_result(tmp_path, ["1.pdf", "2.pdf"]), str(tmp_path / "out"))
    assert z.zip_file.endswith("M12205_Other_Documents.zip")
    assert sorted(zipfile.ZipFile(z.zip_file).namelist()) == ["1.pdf", "2.pdf"]


def test_failed_downloads_preserved_not_zipped(tmp_path):
    f = FailedDownload(doc_no="9", title="bad")
    z = make_zip(_result(tmp_path, ["1.pdf"], [f]), str(tmp_path / "out"))
    assert z.failed_downloads == [f]
    assert zipfile.ZipFile(z.zip_file).namelist() == ["1.pdf"]


def test_no_files_no_zip(tmp_path):
    z = make_zip(_result(tmp_path, []), str(tmp_path / "out"))
    assert z.zip_file is None and z.error_code is None
    assert not (tmp_path / "out").exists()


def test_zip_failure_returns_error_code(tmp_path):
    r = _result(tmp_path, ["1.pdf"])
    r.downloaded_files[0].local_path = str(tmp_path / "missing.pdf")
    z = make_zip(r, str(tmp_path / "out"))
    assert z.zip_file is None and z.error_code == "ZIP_CREATION_FAILED"


def _big(tmp_path, sizes):
    files = []
    for i, size in enumerate(sizes):
        p = tmp_path / f"{i}.bin"
        p.write_bytes(os.urandom(size))  # incompressible
        files.append(DownloadedFile(doc_no=str(i), title=f"doc {i}", local_path=str(p)))
    return DownloadResult(matter_number="M1", document_type="Exhibits", downloaded_files=files)


def test_splits_into_parts_that_each_fit(tmp_path):
    z = make_zip(_big(tmp_path, [600, 600, 600, 600]), str(tmp_path / "out"), max_bytes=1500)
    assert len(z.zip_parts) == 2 and z.zip_file == z.zip_parts[0]
    assert [p.split("_")[-1] for p in z.zip_parts] == ["part1.zip", "part2.zip"]
    names = [n for p in z.zip_parts for n in zipfile.ZipFile(p).namelist()]
    assert sorted(names) == ["0.bin", "1.bin", "2.bin", "3.bin"]
    assert all(os.path.getsize(p) <= 1500 + 400 for p in z.zip_parts)  # zip overhead
    assert not (tmp_path / "out" / "M1_Exhibits.zip").exists()


def test_oversize_file_reported_not_zipped(tmp_path):
    z = make_zip(_big(tmp_path, [500, 5000, 500]), str(tmp_path / "out"), max_bytes=1500)
    assert [f.doc_no for f in z.too_large] == ["1"]
    assert z.zip_parts == []  # the two small files fit in one ZIP, so no "part" naming
    assert sorted(zipfile.ZipFile(z.zip_file).namelist()) == ["0.bin", "2.bin"]


def test_everything_too_large(tmp_path):
    z = make_zip(_big(tmp_path, [5000, 6000]), str(tmp_path / "out"), max_bytes=1500)
    assert z.zip_file is None and len(z.too_large) == 2 and z.error_code is None


def test_under_limit_stays_single_zip(tmp_path):
    z = make_zip(_big(tmp_path, [300, 300]), str(tmp_path / "out"), max_bytes=100_000)
    assert z.zip_parts == [] and z.zip_file.endswith("M1_Exhibits.zip") and z.too_large == []


import os  # noqa: E402  (used by helpers above)
