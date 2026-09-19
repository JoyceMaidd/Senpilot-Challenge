document_counter

Functionality

* Count the number of documents available under each document type for the current matter.
* The document types are:
    * Exhibits
    * Key Documents
    * Other Documents
    * Transcripts
    * Recordings
* Return the counts so they can be included in the response email.
* If a document type has no documents, return 0.
* Continue the workflow even if some document types cannot be counted, unless the matter page itself is unavailable.

Input

{
  "matter_number": "M12205",
  "matter_page": "page_reference"
}

Output

Success

{
  "document_counts": {
    "Exhibits": 13,
    "Key Documents": 5,
    "Other Documents": 21,
    "Transcripts": 0,
    "Recordings": 0
  }
}

→ Return counts to the workflow for email_composer.

Failure

{
  "error_code": "MATTER_PAGE_UNAVAILABLE"
}

→ Invoke email_composer.

Cases

Case	Result
Documents exist under a type	Return the document count
No documents under a type	Return 0
Some document types have no documents	Return 0 for those types and continue
Matter page is unavailable	MATTER_PAGE_UNAVAILABLE → email_composer

Tests

* Verify counts for a known matter.
* Verify document types with no files return 0.
* Verify counts are returned for all five document types.
* Verify an unavailable matter page returns MATTER_PAGE_UNAVAILABLE.

Tools

* Browser automation: Navigate through the document-type tabs and read the available document counts.
* Python: Structure and validate the counts.