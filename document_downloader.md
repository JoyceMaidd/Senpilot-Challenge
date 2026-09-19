# document_downloader

## Functionality

* Download the documents selected by document_finder.
* Use each document's download_reference to locate the correct row on the currently open document tab.
* Download files one at a time. For each file:
  1. Click the row's **GO GET IT** button. A popup window appears.
  2. Click the button in the popup labelled with the file name (e.g. `102674.pdf`). This downloads the file.
  3. If the popup stays open after the download, close it before moving to the next file.
* Save files to /tmp.
* A download counts as successful only when the file exists at its local path and is not empty. Each attempt waits for the file to appear, with a timeout.
* If an individual file download fails, retry that file up to 3 times.
* After 3 failed attempts, record the failure and continue downloading the remaining files.
* Return both successful and failed downloads.

## Input

```json
{
  "browser_session": "active",
  "matter_number": "M12205",
  "document_type": "Other Documents",
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
```

## Output

### Success

All downloads succeed:

```json
{
  "matter_number": "M12205",
  "document_type": "Other Documents",
  "downloaded_files": [
    {
      "doc_no": "102674",
      "title": "Board Order",
      "local_path": "/tmp/102674.pdf"
    }
  ],
  "failed_downloads": []
}
```

Some downloads fail:

```json
{
  "matter_number": "M12205",
  "document_type": "Other Documents",
  "downloaded_files": [
    {
      "doc_no": "102674",
      "title": "Board Order",
      "local_path": "/tmp/102674.pdf"
    }
  ],
  "failed_downloads": [
    {
      "doc_no": "102675",
      "title": "Example Document",
      "error": "DOWNLOAD_FAILED"
    }
  ]
}
```

`local_path` is the path of the file as actually saved. Its name comes from the popup button (the document number plus the extension).

→ Pass downloaded_files to zip_tool.

### Failure

```json
{
  "error_code": "DOCUMENT_DOWNLOAD_FAILED"
}
```

→ Invoke email_composer.

## Cases

| Case | Result |
|---|---|
| All selected documents download successfully | Return all files → zip_tool |
| An individual download fails | Retry that file up to 3 times |
| A file still fails after 3 attempts | Record it in failed_downloads and continue |
| Every selected file fails | Return an empty downloaded_files with all files in failed_downloads and continue (zip_tool must handle an empty list) |
| No documents selected | Return empty lists and continue to zip_tool |
| Browser/session unavailable | DOCUMENT_DOWNLOAD_FAILED → email_composer |

## Tests

* Verify a selected document downloads successfully (click GO GET IT, then the popup button) and the file is saved to /tmp with the expected name.
* Verify a failed file is retried 3 times.
* Verify one failed file does not stop the remaining downloads.
* Verify the popup does not block the next download.
* Verify an empty document list returns empty results.

## Tools

* Browser automation: Click GO GET IT, click the file button in the popup, and close the popup if needed.
* Python: Retry logic, checking that each file exists and is not empty, and file handling.