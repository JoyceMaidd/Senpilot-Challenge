document_finder

Functionality

* Validate that document_type is one of:
    * Exhibits
    * Key Documents
    * Other Documents
    * Transcripts
    * Recordings
* Do not treat Hearings or Related Matters as document types.
* Read the document count from the requested tab’s label (e.g. Other Documents - 43).
* If the count is 0, do not click the tab; return an empty list.
* If a No Matching Records popup appears, click OK and continue with an empty list.
* Otherwise, open the requested document-type tab and identify the available documents.
* Select the first 10 documents in the order displayed on the page. Do not re-sort. If fewer than 10 exist, select all.
* The page displays only 10 rows at a time, even when more documents exist.
* Only select documents from the requested document type.
* Leave the requested tab open so document_downloader can use the GO GET IT buttons.

Input

{
  "matter_number": "M12205",
  "matter_page": "page_reference",
  "document_type": "Other Documents"
}

Output

Success

{
  "documents": [
    {
      "doc_no": "102674",
      "title": "Board Order",
      "extension": ".pdf",
      "date": "07/08/2026",
      "security": "Public",
      "download_reference": "Other Documents:102674"
    }
  ]
}

The list contains 0–10 documents.

The page does not display the actual filename. It provides:

* doc_no: Doc No, or Exhibit No on the Exhibits tab
* title
* extension
* date: Date, or Date Filed on the Exhibits tab
* security
* download_reference: {document_type}:{doc_no}

The document type is included in download_reference because the same document can appear in multiple tabs.

→ Pass documents to document_downloader.

Failure

{
  "error_code": "DOCUMENT_FIND_FAILED"
}

→ Invoke email_composer.

Cases

Case	Result
10+ documents	Select first 10 as displayed
Fewer than 10	Select all
Count is 0	Do not click tab; return empty list
No Matching Records popup	Click OK; return empty list
Invalid document type	DOCUMENT_FIND_FAILED → email_composer
Matter page unavailable	DOCUMENT_FIND_FAILED → email_composer
Tab/list fails to load	DOCUMENT_FIND_FAILED → email_composer
Documents from another type are visible	Do not select them

Tests

* Verify the correct document-type tab is selected.
* Verify only requested-type documents are selected.
* Verify no more than 10 documents are returned.
* Verify the first 10 displayed rows are selected without re-sorting.
* Verify fewer than 10 documents are all returned.
* Verify a zero-count tab returns an empty list without clicking it.
* Verify the No Matching Records popup is dismissed.
* Verify an invalid type such as Hearings returns DOCUMENT_FIND_FAILED.
* Verify Exhibits correctly handles Exhibit No and Date Filed.

Tools

* Browser automation: Read tab counts, navigate tabs, read document rows, and leave the requested tab open.
* Python: Structure the document data and enforce the 10-document limit.