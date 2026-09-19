# metadata_extractor

## Functionality

* Extract available matter metadata from the matter page.
* Read only: do not click tabs or navigate away from the matter page, since `document_counter` and `document_finder` use the same page.
* Store unavailable or empty fields as None.
* Continue the workflow regardless of missing metadata.
* Fail only if the matter page is unavailable or cannot be accessed.

## Input

```json
{
  "matter_number": "M12205",
  "matter_page": "page_reference"
}
```

## Output

### Success

```json
{
  "matter_number": "M12205",
  "status": "...",
  "title": "...",
  "description": "...",
  "type": "...",
  "category": "...",
  "date_received": "...",
  "decision_date": "...",
  "outcome": "..."
}
```

Any field without available data should be:

None

Every field except `matter_number` is optional (`Optional[str]` in Pydantic, which serializes to `null` in JSON). `matter_number` is always present because it comes from the input.

→ Continue workflow. The metadata is passed to `email_composer`.

### Failure

```json
{
  "error_code": "MATTER_PAGE_UNAVAILABLE"
}
```

→ Invoke email_composer.

## Cases

| Case | Result |
|---|---|
| All metadata available | Extract and continue |
| Some metadata missing (e.g. Outcome is blank for a matter still awaiting a decision) | Set missing fields to None and continue |
| Matter page unavailable | MATTER_PAGE_UNAVAILABLE → email_composer |

## Tests

* Verify metadata is extracted from a known matter.
* Verify missing fields become None.
* Verify the workflow continues when metadata is incomplete.
* Verify an unavailable matter page returns MATTER_PAGE_UNAVAILABLE.

## Tools

* Browser automation: Read the matter page and extract metadata.
* Pydantic: Validate the metadata structure.
* Python: Handle missing values and structure the output.