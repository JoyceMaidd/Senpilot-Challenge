# Senpilot's Technical Assignment

## Challenge

We are building an AI agent platform for utilities like Toronto Hydro or Hydro One. Utilities have to make large, detailed regulatory filings to get projects approved and justify customer rates.

Our Regulatory Agent helps automate the research that goes into these filings by finding examples, precedents, and approval patterns from past cases. And this challenge focuses on the data ingestion side, developing a pipeline to collect filings and build the searchable database that lies under the Regulatory Agent's research capabilities.

Your task is to build an AI agent that (1) fetches <u>up to</u> 10 documents of a given type from a website, and (2) ZIPs those documents and sends the ZIP over email. More specifically:

### 1. A user will email your agent a "matter number" and a document type

- **A.** Matter numbers take the form M12205, M12383, etc.
- **B.** Document types can be:
  - a. Exhibits
  - b. Key Documents
  - c. Other Documents
  - d. Transcripts
  - e. Recordings
- **C.** Example: "Hi Agent, Can you give me Other Documents files from M12205? Thanks!"

### 2. Your agent must then fetch the files

- **A.** Go to <https://uarb.novascotia.ca/fmi/webd/UARB15>
- **B.** Input the matter number in the "Go Directly to Matter" box
- **C.** Press Search
- **D.** Go to the relevant tab corresponding to the document type
- **E.** Download <u>up to</u> 10 documents (use the "Go Get It" button)
- **F.** Compress those documents into a ZIP

### 3. Your agent must then send an email response

- **A.** The ZIP must be included as an attachment
- **B.** The email should provide a total count of all files within that matter number
- **C.** The email should also summarize key metadata related to the matter number
- **D.** Example:

> "Hi User,
>
> M12205 is about the Halifax Regional Water Commission - Windsor Street Exchange Redevelopment Project - $69,270,000. It relates to Capital Expenditure within the Water category. The matter had an initial filing on April 7, 2025 and a final filing on October 23, 2025. I found 13 Exhibits, 5 Key Documents, 21 Other Documents, and no Transcripts or Recordings. I downloaded 10 out of the 21 Other Documents and am attaching them as a ZIP here."

Below are some screenshots of the website pages the agent will need to navigate through:

*(Screenshots omitted.)*
