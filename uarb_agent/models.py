"""Shared data models and constants. Field names follow the component docs in components/."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

DOCUMENT_TYPES = [
    "Exhibits",
    "Key Documents",
    "Other Documents",
    "Transcripts",
    "Recordings",
]

MAX_DOCUMENTS = 10


class PipelineError(Exception):
    """A component failed in a way that should end in an error email."""

    def __init__(self, error_code: str, detail: str = ""):
        super().__init__(f"{error_code}: {detail}" if detail else error_code)
        self.error_code = error_code
        self.detail = detail


class ParsedRequest(BaseModel):
    matter_number: str
    document_type: str
    requester_email: str


class Metadata(BaseModel):
    """Matter header fields. Everything but matter_number may be None.

    `type` and `category` follow the site's own labels (Type above Category), e.g.
    type="Water", category="Capital Expenditure Approvals".
    """

    matter_number: str
    status: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    category: Optional[str] = None
    date_received: Optional[str] = None
    decision_date: Optional[str] = None
    outcome: Optional[str] = None


class Document(BaseModel):
    doc_no: str
    title: str
    extension: str
    date: str
    security: str
    download_reference: str


class DownloadedFile(BaseModel):
    doc_no: str
    title: str
    local_path: str


class FailedDownload(BaseModel):
    doc_no: str
    title: str
    error: str = "DOWNLOAD_FAILED"


class DownloadResult(BaseModel):
    matter_number: str
    document_type: str
    downloaded_files: list[DownloadedFile] = Field(default_factory=list)
    failed_downloads: list[FailedDownload] = Field(default_factory=list)


class ZipResult(BaseModel):
    matter_number: str
    document_type: str
    zip_file: Optional[str] = None
    # Set when the files did not fit in one email: every part, in order (zip_file is the first).
    zip_parts: list[str] = Field(default_factory=list)
    # Downloaded files too large to attach to any email.
    too_large: list[DownloadedFile] = Field(default_factory=list)
    failed_downloads: list[FailedDownload] = Field(default_factory=list)
    error_code: Optional[str] = None


class ComposerInput(BaseModel):
    requester_email: str
    matter_number: Optional[str] = None
    document_type: Optional[str] = None
    metadata: Optional[Metadata] = None
    document_counts: Optional[dict[str, int]] = None
    downloaded_files: list[DownloadedFile] = Field(default_factory=list)
    failed_downloads: list[FailedDownload] = Field(default_factory=list)
    zip_file: Optional[str] = None
    zip_parts: list[str] = Field(default_factory=list)
    too_large: list[DownloadedFile] = Field(default_factory=list)
    # doc_nos of downloaded documents whose Security is not Public (the site serves a notice page for these).
    confidential_docs: list[str] = Field(default_factory=list)
    error_code: Optional[str] = None


class EmailContent(BaseModel):
    recipient: str
    subject: str
    body: str
    attachment: Optional[str] = None
    # Follow-up emails when the ZIP had to be split: (subject, body, attachment).
    extra_parts: list[tuple[str, str, str]] = Field(default_factory=list)
