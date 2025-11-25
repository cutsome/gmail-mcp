# MCP Gmail Server

An MCP (Model Context Protocol) server that wraps the Gmail API.

## Features

Provides the following 4 tools:

- `gmail.search_messages`: Search Gmail and retrieve a list of message IDs
- `gmail.get_message`: Retrieve detailed information for the specified message ID
- `gmail.get_attachments`: Retrieve a list of attachments for the specified message
- `gmail.get_attachment_data`: Retrieve attachment data for the specified attachment (base64 encoded)

## Setup

### 1. Install Dependencies

```bash
cd mcp-gmail-server
uv sync
```

### 2. Google Cloud Console Configuration

Follow the official documentation to enable Gmail API and create OAuth 2.0 credentials:

1. [Python quickstart | Gmail](https://developers.google.com/workspace/gmail/api/quickstart/python) - Follow "Set up your environment" section
2. [Create access credentials](https://developers.google.com/workspace/guides/create-credentials) - Create OAuth client ID

> **Note:** When creating OAuth client ID, select **"Desktop app"** as the application type.

After completing the steps, download the credentials JSON file and rename it to `client_secret.json`.

### 3. Place Credentials File

Place the `client_secret.json` file downloaded from Google Cloud Console in the `mcp-gmail-server` directory:

```
mcp-gmail-server/
  ├─ client_secret.json  # Place here
  └─ ...
```

#### Custom Path Specification (Optional)

If you want to place `client_secret.json` in a different location, you can specify the path using an environment variable:

```bash
export GOOGLE_CLIENT_SECRET_PATH="/path/to/client_secret.json"
```

#### First-Time Authentication

On first startup, the OAuth2 flow will be executed and authentication will be requested in the browser.
After authentication is complete, a `token.json` file will be created and the refresh token will be saved.
Subsequent runs will automatically authenticate using this `token.json`.

## Usage

### Start as MCP Server

```bash
uv run mcp-gmail-server
```

The server processes the MCP protocol via stdio.

### Direct Execution (for testing)

```bash
uv run python -m mcp_gmail_server.main
```

### MCP Client Configuration (Cursor, etc.)

Add the following to your `mcp.json` (or `.cursor/mcp.json` for Cursor):

```json
{
  "mcpServers": {
    "gmail": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/mcp-gmail-server", "mcp-gmail-server"]
    }
  }
}
```

Replace `/path/to/mcp-gmail-server` with the actual path to this project directory.

### Debugging with MCP Inspector

MCP Inspector allows you to debug the MCP server with a browser-based UI. You can test tools, check resources, test prompts, etc.

```bash
# Using Makefile (recommended)
make debug

# Or execute directly
npx @modelcontextprotocol/inspector uv run mcp-gmail-server
```

When you run this command:
1. MCP Inspector will start and the browser will open automatically (default: `http://localhost:5173`)
2. Server connection status, available tools, and metadata will be displayed
3. You can test each tool in the "Tools" tab
4. You can execute tools with custom inputs and check responses

**Port Customization:**

```bash
CLIENT_PORT=8080 SERVER_PORT=9000 npx @modelcontextprotocol/inspector uv run mcp-gmail-server
```

## Tool Details

### gmail.search_messages

Search Gmail and retrieve a list of message IDs.

**Parameters:**
- `query` (required): Gmail search query (e.g., `"after:2025/1/1"`, `"from:example@gmail.com"`)
- `max_results` (optional): Maximum number of results (default: 100)

**Return Value:**
```json
[
  {
    "message_id": "1234567890",
    "thread_id": "0987654321"
  },
  ...
]
```

### gmail.get_message

Retrieve detailed information for the specified message ID.

**Parameters:**
- `message_id` (required): ID of the message to retrieve

**Return Value:**
```json
{
  "message_id": "1234567890",
  "thread_id": "0987654321",
  "subject": "Email Subject",
  "from": "sender@example.com",
  "to": "recipient@example.com",
  "received_at": "2025-01-31T10:23:45+09:00",
  "body_text": "Email body..."
}
```

### gmail.get_attachments

Retrieve a list of attachments for the specified message.

**Parameters:**
- `message_id` (required): ID of the message to retrieve attachments from

**Return Value:**
```json
[
  {
    "attachment_id": "att123",
    "file_name": "receipt.pdf",
    "mime_type": "application/pdf",
    "size": 12345
  },
  ...
]
```

### gmail.get_attachment_data

Retrieve attachment data for the specified attachment (base64 encoded).

**Parameters:**
- `message_id` (required): ID of the message containing the attachment
- `attachment_id` (required): ID of the attachment to retrieve

**Return Value:**
```json
{
  "attachment_id": "att123",
  "data": "base64 encoded data",
  "size": 12345
}
```

## Troubleshooting

### Authentication Errors

- Check if the `client_secret.json` file is placed in the `mcp-gmail-server` directory
- Verify that the contents of `client_secret.json` are correct (use the file downloaded from Google Cloud Console as-is)
- Delete the `token.json` file and try authenticating again

### Gmail API Errors

- Check if Gmail API is enabled
- Verify that the OAuth 2.0 credentials scope is correct (`https://www.googleapis.com/auth/gmail.readonly`)

## License

This project is licensed under the [MIT License](LICENSE).
