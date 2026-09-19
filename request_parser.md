request_parser

Functionality

* Parse the incoming email and extract:
    * matter_number
    * document_type
    * requester_email
* Normalize extracted values before validation.
* Validate the normalized values.
* If both are valid, invoke browser_open.
* If validation fails, pass the appropriate error_code to email_composer.
* Do not interact with the UARB website.

Input

email

Output

Valid request

{
  "matter_number": "M12205",
  "document_type": "Other Documents",
  "requester_email": "user@example.com"
}

→ Invoke browser_open.

Invalid request

{
  "requester_email": "user@example.com",
  "error_code": "INVALID_MATTER_NUMBER"
}

→ Invoke email_composer.

Possible error codes:

MISSING_MATTER_NUMBER
INVALID_MATTER_NUMBER
MISSING_DOCUMENT_TYPE
INVALID_DOCUMENT_TYPE
INVALID_INPUT

Cases

Matter number

Normalize common variations into the canonical format:

m12205  → M12205
12205   → M12205
M12205  → M12205

After normalization, the value must follow:

M + exactly 5 digits

Examples:

M12205   → valid
m12205   → normalize → M12205 → valid
12205    → normalize → M12205 → valid
M1234    → invalid
M123456  → invalid
1234     → invalid
ABC123   → invalid

Document type

Normalize capitalization, whitespace, and common natural-language variations into one of the canonical document types:

Exhibits
Key Documents
Other Documents
Transcripts
Recordings

Examples:

exhibits              → Exhibits
EXHIBITS              → Exhibits
key documents         → Key Documents
other docs            → Other Documents
other documents       → Other Documents
transcript            → Transcripts
recording              → Recordings

If the input cannot be mapped to a supported document type, return INVALID_DOCUMENT_TYPE.

Request handling

Case	Result
Valid/normalizable matter + valid/normalizable document type	Continue to browser_open
Missing matter number	MISSING_MATTER_NUMBER → email_composer
Unnormalizable matter number	INVALID_MATTER_NUMBER → email_composer
Missing document type	MISSING_DOCUMENT_TYPE → email_composer
Unnormalizable document type	INVALID_DOCUMENT_TYPE → email_composer
Unparseable/irrelevant email	INVALID_INPUT → email_composer
Multiple matter numbers	INVALID_INPUT → email_composer

Tests

* Normalize m12205 → M12205
* Normalize 12205 → M12205
* Reject matter numbers that cannot be normalized to M + 5 digits
* Normalize capitalization and common variations of document types
* Accept all five supported document types
* Test missing matter number/document type
* Test invalid matter number/document type
* Test irrelevant or unparseable emails
* Test multiple matter numbers
* Verify valid requests invoke browser_open
* Verify invalid requests invoke email_composer with the correct error_code

Tools

* LLM: Extract and interpret natural-language requests.
* Pydantic: Define the structured request and error schemas.
* Regex: Validate the normalized matter number.
* Python: Normalization, validation, error handling, and routing.
* Email API: Receive the email and obtain requester_email.