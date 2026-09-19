# matter_search

## Functionality

* Use the active browser session to search for the requested matter.
* Input matter_number into the "Go Directly to Matter" field.
* Click Search.
* Detect whether the matter was successfully found.
* Detect the "No Records Found" popup and route the request to email_composer.
* Pass the matter page/context to downstream components when successful.

## Input

```json
{
  "browser_session": "active",
  "matter_number": "M12205"
}
```

## Output

### Success

```json
{
  "matter_number": "M12205",
  "matter_page": "page_reference"
}
```

→ Invoke metadata_extractor, document_counter, and document_finder.

### Failure

```json
{
  "error_code": "MATTER_NOT_FOUND"
}
```

→ Invoke email_composer.

## Cases

| Case | Result |
|---|---|
| Matter exists | Open matter page → continue workflow |
| Valid-format matter does not exist | Detect "No Records Found" popup → MATTER_NOT_FOUND → email_composer |
| Search/page interaction fails | Return appropriate search error → email_composer |

The expected "No Records Found" popup contains:

> No Records Found
> No records matched your search request.
> Click OK to return to Search page.

## Tests

* Search for an existing matter such as M12205 and verify the matter page opens.
* Search for a non-existent matter such as M99999 and verify MATTER_NOT_FOUND is returned.

## Tools

* Browser automation: Enter the matter number, click Search, read the resulting page/popup, and retain the matter page reference.