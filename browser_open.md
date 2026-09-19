browser_open

Functionality

* Open the Nova Scotia UARB Public Documents Database.
* Ensure the browser can access the website from a Canadian network/VPN connection.
* Retry opening the website up to 3 times if the initial attempt fails.
* If all attempts fail, pass the error to email_composer.
* If successful, pass the active browser session to matter_search.

Input

None

Target website:

https://uarb.novascotia.ca/fmi/webd/UARB15

Output

Success

{
  "browser_session": "active"
}

→ Invoke matter_search.

Failure

{
  "error_code": "BROWSER_OPEN_FAILED"
}

→ Invoke email_composer.

Cases

Case	Result
Website opens successfully	Continue to matter_search
Initial attempt fails	Retry
Website fails after 3 attempts	BROWSER_OPEN_FAILED → email_composer
Website is inaccessible without Canadian VPN	Connect/use Canadian VPN and retry

Tests

* Verify the website can be opened successfully.
* Verify a failed attempt is retried up to 3 times.
* Verify failure after 3 attempts sends BROWSER_OPEN_FAILED to email_composer.

Tools

* Browser automation: Open and interact with the UARB website.
* VPN/network configuration: Ensure access through a Canadian IP/network.