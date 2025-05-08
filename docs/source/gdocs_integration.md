# Google Docs Integration

CellMage provides integration with Google Docs through the `%gdocs` magic command, allowing you to fetch Google Document content directly into your notebook and use it as context for LLM queries.

## Installation

To use the Google Docs integration, install CellMage with the `gdocs` extra:

```bash
pip install "cellmage[gdocs]"
```

This will install the necessary dependencies including:
- `google-auth`
- `google-auth-oauthlib`
- `google-auth-httplib2`
- `google-api-python-client`

## Configuration

The Google Docs integration requires OAuth 2.0 credentials or a service account. You can configure it using environment variables:

```bash
# OAuth configuration (default)
CELLMAGE_GDOCS_AUTH_TYPE=oauth
CELLMAGE_GDOCS_TOKEN_PATH=~/.cellmage/gdocs_token.pickle
CELLMAGE_GDOCS_CREDENTIALS_PATH=~/.cellmage/gdocs_credentials.json

# Or service account configuration
CELLMAGE_GDOCS_AUTH_TYPE=service_account
CELLMAGE_GDOCS_SERVICE_ACCOUNT_PATH=~/.cellmage/gdocs_service_account.json
```

### OAuth 2.0 Authentication

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or use an existing one
3. Enable the Google Docs API and Google Drive API
4. Create OAuth 2.0 credentials and download the credentials JSON file
5. Rename it to `gdocs_credentials.json` and place it in the `~/.cellmage/` directory
6. The first time you use the integration, a browser window will open to authenticate
7. Make sure to grant access to both Documents and Drive when authorizing

### Service Account Authentication

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or use an existing one
3. Enable the Google Docs API and Google Drive API
4. Create a Service Account and download the JSON key file
5. Rename it to `gdocs_service_account.json` and place it in the `~/.cellmage/` directory
6. Share your Google Documents with the service account email address

### Required Scopes

By default, CellMage uses the following scopes:
- `https://www.googleapis.com/auth/documents.readonly` - For reading documents
- `https://www.googleapis.com/auth/drive.readonly` - For searching and listing documents

You can customize these with the `CELLMAGE_GDOCS_SCOPES` environment variable:

```bash
# Optional: Override the default scopes (comma-separated)
CELLMAGE_GDOCS_SCOPES=https://www.googleapis.com/auth/documents.readonly,https://www.googleapis.com/auth/drive.readonly
```

## Basic Usage

To fetch a specific Google Document by ID:

```ipython
%gdocs your_google_doc_id
```

To fetch a document using its URL:

```ipython
%gdocs https://docs.google.com/document/d/YOUR_DOC_ID/edit
```

This fetches the document content and adds it as a user message in the chat history.

## Advanced Usage

### Searching for Documents

You can search for Google Docs documents containing specific terms:

```ipython
%gdocs --search "project documentation"
```

This returns a table of matching documents with their metadata.

To customize the number of search results:

```ipython
%gdocs --search "project documentation" --max-results 20
```

### Fetching Document Content from Search Results

To fetch and display content from the top search results:

```ipython
%gdocs --search "project documentation" --content
```

By default, this fetches content for the top 3 documents. You can customize this:

```ipython
%gdocs --search "project documentation" --content --max-content 5
```

### Filtering Search Results

You can filter search results by various criteria:

```ipython
# Filter by author/owner
%gdocs --search "project documentation" --author "user@example.com"

# Filter by creation date (supports natural language)
%gdocs --search "project documentation" --created-after "3 days ago"
%gdocs --search "project documentation" --created-before "2023-12-31"

# Filter by modification date
%gdocs --search "project documentation" --modified-after "last week"
%gdocs --search "project documentation" --modified-before "2023-12-31"

# Sort results
%gdocs --search "project documentation" --order-by "modifiedTime"  # Options: relevance, modifiedTime, createdTime, name
```

### Authentication Options

You can specify the authentication type for a specific command:

```ipython
%gdocs your_google_doc_id --auth-type service_account
```

### System Context

To add the document as system context instead of a user message:

```ipython
%gdocs your_google_doc_id --system
```

### Display Only

To only display the document content without adding it to chat history:

```ipython
%gdocs your_google_doc_id --show
```

### Command Options

| Option | Description |
|--------|-------------|
| `--system` | Add as system message instead of user message |
| `--show` | Only display the content without adding to chat history |
| `--auth-type` | Authentication type to use (`oauth` or `service_account`) |
| `--search` | Search for Google Docs files containing the specified term |
| `--content` | Retrieve and display content for search results |
| `--max-results` | Maximum number of search results to return (default: 10) |
| `--max-content` | Maximum number of documents to retrieve content for (default: 3) |
| `--author` | Filter documents by author/owner email |
| `--created-after` | Filter documents created after this date (YYYY-MM-DD or natural language) |
| `--created-before` | Filter documents created before this date |
| `--modified-after` | Filter documents modified after this date |
| `--modified-before` | Filter documents modified before this date |
| `--order-by` | How to order search results (`relevance`, `modifiedTime`, `createdTime`, `name`) |

## Using Google Docs Content with LLM Queries

After fetching a Google Document, you can directly reference it in your LLM prompts:

```ipython
# First, fetch the document content
%gdocs https://docs.google.com/document/d/YOUR_DOC_ID/edit

# Then, reference it in your prompt
%%llm
Based on the Google Document above, summarize the key points and provide actionable insights.
```

## Troubleshooting

### Authentication Issues

1. **OAuth Error**: If you see an error with OAuth authentication, ensure your credentials file is correct and the Google Docs API is enabled in your project.

2. **Service Account Error**: If using a service account, ensure the document is shared with the service account email address.

3. **Token Refresh Error**: If your token expires, you might need to re-authenticate. Delete the token file and run the command again.

### Access Permission Issues

1. **Document Not Found**: Ensure the document exists and you have access to it.

2. **Permission Denied**: Ensure you have at least read access to the document.

### Connection Problems

1. **API Rate Limits**: Google API has rate limits. If you hit them, wait a few minutes.

2. **Network Issues**: Check your internet connection.

For persistent issues, examine the CellMage log:

```python
import logging
from cellmage.utils.logging import setup_logging
setup_logging(level=logging.DEBUG)
# The logs will be written to cellmage.log in your working directory
```
