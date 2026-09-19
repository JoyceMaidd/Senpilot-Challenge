ZIP Tool

Functionality

* Compress all successfully downloaded documents into a single ZIP archive.
* Use the matter_number and document_type to generate the ZIP filename.
* Save the ZIP archive in /tmp.
* If some documents failed to download, ZIP only the successful files and preserve the failed-download information for email_composer.
* If no documents were downloaded, do not create an empty ZIP.
* Pass the result to email_composer regardless of whether ZIP creation succeeds or fails.

Input

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

Output

Successful ZIP creation:

{
  "matter_number": "M12205",
  "document_type": "Other Documents",
  "zip_file": "/tmp/M12205_Other_Documents.zip",
  "failed_downloads": []
}

→ email_composer

If some documents failed:

{
  "matter_number": "M12205",
  "document_type": "Other Documents",
  "zip_file": "/tmp/M12205_Other_Documents.zip",
  "failed_downloads": [
    {
      "doc_no": "102675",
      "title": "Example Document",
      "error": "DOWNLOAD_FAILED"
    }
  ]
}

→ email_composer

If no files were downloaded:

{
  "matter_number": "M12205",
  "document_type": "Other Documents",
  "zip_file": null,
  "failed_downloads": []
}

→ email_composer

If ZIP creation fails:

{
  "matter_number": "M12205",
  "document_type": "Other Documents",
  "zip_file": null,
  "error_code": "ZIP_CREATION_FAILED"
}

→ email_composer

Cases

* All downloaded files are successfully compressed → email_composer.
* Some downloads failed → create ZIP with successful files only → email_composer.
* No files downloaded → no ZIP → email_composer.
* ZIP creation fails → pass error to email_composer.

Tests

* Verify multiple downloaded files are included in the ZIP.
* Verify failed downloads are not included.
* Verify ZIP filename contains the correct matter number and document type.
* Verify no ZIP is created when there are no downloaded files.
* Verify ZIP creation failure returns the correct error code.

Tools

* Python zipfile
* Python file handling