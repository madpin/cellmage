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
3. Enable the Google Docs API
4. Create OAuth 2.0 credentials and download the credentials JSON file
5. Rename it to `gdocs_credentials.json` and place it in the `~/.cellmage/` directory
6. The first time you use the integration, a browser window will open to authenticate

### Service Account Authentication

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or use an existing one
3. Enable the Google Docs API
4. Create a Service Account and download the JSON key file
5. Rename it to `gdocs_service_account.json` and place it in the `~/.cellmage/` directory
6. Share your Google Documents with the service account email address

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
