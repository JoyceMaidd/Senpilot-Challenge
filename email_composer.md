# email_composer

## Functionality

* Compose the reply email to the requester and pass it to email_sender.
* Receives either the full result of a successful run, or an `error_code` from any earlier component.
* Choose the template from `error_code` first. If there is none, choose by download result.
* Attach the ZIP only when `zip_file` is not null.
* Omit any sentence whose data is None or unavailable. Never stop because data is missing.
* Format dates as `April 7, 2025`. Format counts of 0 as `no <type>`.
* Any unrecognized `error_code` uses the generic template.

## Input

```json
{
  "requester_email": "user@example.com",
  "matter_number": "M12205",
  "document_type": "Other Documents",
  "metadata": {
    "title": "Halifax Regional Water Commission - Windsor Street Exchange Redevelopment Project",
    "description": "$69,270,000",
    "type": "Capital Expenditure",
    "category": "Water",
    "date_received": "04/07/2025",
    "decision_date": "10/23/2025",
    "status": "Closed"
  },
  "document_counts": {
    "Exhibits": 13,
    "Key Documents": 5,
    "Other Documents": 21,
    "Transcripts": 0,
    "Recordings": 0
  },
  "downloaded_files": [{ "doc_no": "102674", "title": "Board Order", "local_path": "/tmp/102674.pdf" }],
  "failed_downloads": [],
  "zip_file": "/tmp/M12205_Other_Documents.zip",
  "error_code": null
}
```

Only `requester_email` is guaranteed. On errors, other fields may be missing.

## Output

```json
{
  "recipient": "user@example.com",
  "subject": "UARB Documents - M12205",
  "body": "...",
  "attachment": "/tmp/M12205_Other_Documents.zip"
}
```

`attachment` is null when there is no ZIP. If `matter_number` is unknown, the subject is `UARB Documents Request`.

→ Invoke email_sender.

## Templates

Placeholders: `{matter}`, `{type}` (document type), `{n}` (downloaded), `{total}` (count for the requested type), `{failed}` (failed downloads).

`{summary}` is the shared matter summary, built from metadata and counts:

> {matter} is about the {title} - {description}. It relates to {type} within the {category} category. The matter had an initial filing on {date_received} and a final filing on {decision_date}. I found 13 Exhibits, 5 Key Documents, 21 Other Documents, and no Transcripts or Recordings.

### Results (no error_code)

| Case | Body |
|---|---|
| Success | Hi User,<br><br>{summary} I downloaded {n} out of the {total} {type} and am attaching them as a ZIP here. |
| Partial downloads | Hi User,<br><br>{summary} I downloaded {n} out of the {total} {type} and am attaching them as a ZIP here. {failed} file(s) could not be downloaded after 3 attempts: {doc_no – title list}. |
| No documents of requested type | Hi User,<br><br>{summary} There are no {type} for this matter, so there is no ZIP to attach. |

Success is used when `failed_downloads` is empty. Partial is used when it is not empty and `zip_file` is set. "Success" also covers matters with more than 10 documents. Only up to 10 are downloaded, and `{n}` reflects that.

### Errors (error_code)

| error_code | Source | Body |
|---|---|---|
| MISSING_MATTER_NUMBER | request_parser | Hi User,<br><br>I couldn't find a matter number in your request. Please reply with one in the form M12205. |
| INVALID_MATTER_NUMBER | request_parser | Hi User,<br><br>The matter number in your request isn't valid. Matter numbers are the letter M followed by 5 digits, such as M12205. Please check it and try again. |
| MISSING_DOCUMENT_TYPE | request_parser | Hi User,<br><br>I couldn't find a document type in your request. Please choose one of: Exhibits, Key Documents, Other Documents, Transcripts, or Recordings. |
| INVALID_DOCUMENT_TYPE | request_parser | Hi User,<br><br>I don't recognize the document type in your request. Please choose one of: Exhibits, Key Documents, Other Documents, Transcripts, or Recordings. |
| INVALID_INPUT | request_parser | Hi User,<br><br>I couldn't understand your request, or it contained more than one matter number. Please send one matter number and one document type, for example: "Can you give me Other Documents files from M12205?" |
| BROWSER_OPEN_FAILED | browser_open | Hi User,<br><br>I couldn't reach the UARB website after several attempts, so I couldn't process {matter}. Please try again later. |
| MATTER_NOT_FOUND | matter_search | Hi User,<br><br>I couldn't find {matter} on the UARB website. Please check the matter number and try again. |
| MATTER_PAGE_UNAVAILABLE | metadata_extractor, document_counter | Hi User,<br><br>I found {matter}, but its page couldn't be loaded, so I couldn't retrieve its details or documents. Please try again later. |
| DOCUMENT_FIND_FAILED | document_finder | Hi User,<br><br>{summary} However, I couldn't load the list of {type}, so I couldn't download any files. Please try again later. |
| DOCUMENT_DOWNLOAD_FAILED | document_downloader | Hi User,<br><br>{summary} I found the {type}, but the download process failed, so I have no files to send. Please try again later. |
| ZIP_CREATION_FAILED | zip_tool | Hi User,<br><br>{summary} I downloaded {n} out of the {total} {type}, but I couldn't create the ZIP file, so nothing is attached. Please try again later. |
| Any other code | any | Hi User,<br><br>Something went wrong while processing your request for {matter}. Please try again later. |

For errors that use `{summary}`, include it only if metadata and counts are available. Otherwise start with the sentence after it. Error emails never carry an attachment.

## Tests

* Success email has the metadata sentence, all five counts, the download count, and the ZIP attached.
* Partial-download email lists failed files and attaches the ZIP.
* No-document email has no attachment.
* Each error_code above produces its own template and no attachment.
* An unknown error_code produces the generic template.
* Missing (None) metadata is omitted without stopping the email.
* Parser errors with only `requester_email` and `error_code` still produce a valid email.

## Tools

* Python: Template selection and email construction.
* Pydantic: Validate the input and output.
* Email API/message format: Prepare the attachment.
