# ⚙️ Configuration

CellMage offers multiple ways to configure its behavior, from environment variables to runtime commands. This flexibility allows you to set up your environment once and then make temporary adjustments as needed.

## 🔧 Configuration Methods

### 1. Environment Variables

Environment variables provide a system-wide way to configure CellMage. All environment variables use the `CELLMAGE_` prefix.

```bash
# Example: Setting environment variables in your shell
export CELLMAGE_API_KEY="your_openai_api_key"
export CELLMAGE_DEFAULT_MODEL="gpt-4o"
export CELLMAGE_PERSONAS_DIRS="~/my_personas,~/project_personas"
```

### 2. `.env` File

You can also place a `.env` file in your working directory with your configuration:

```ini
# Example .env file
CELLMAGE_API_KEY=your_openai_api_key
CELLMAGE_DEFAULT_MODEL=gpt-4o
CELLMAGE_PERSONAS_DIRS=~/my_personas,~/project_personas
```

This approach is particularly useful for project-specific settings and avoids exposing sensitive information in your environment or code.

### 3. Runtime Configuration

Use the `%llm_config` magic command to change settings during a session:

```ipython
# View current configuration
%llm_config --status

# Change the default model
%llm_config --model gpt-4o-mini

# Set parameter overrides for the session
%llm_config --set-override temperature 0.7
```

See the [Magic Commands](./magic_commands.md) documentation for a complete reference of all available configuration commands.

### 4. Model Mapping File

CellMage supports model aliasing through a YAML configuration file named `cellmage_models.yml`, which allows you to create shorthand names for models:

```yaml
# Example cellmage_models.yml
mappings:
  g4: gpt-4o
  g4m: gpt-4o-mini
  g3: gpt-3.5-turbo
  claud3h: claude-3-haiku
  claud3s: claude-3-sonnet
```

CellMage will automatically look for this file in your working directory, or you can specify a custom path with the `CELLMAGE_MODEL_MAPPINGS_FILE` environment variable.

## 📋 Configuration Options

Here's the complete list of configuration options organized by category:

### Core Settings

| Environment Variable | Description | Default Value | Type |
|---------------------|-------------|--------------|------|
| `CELLMAGE_API_KEY` | Your LLM API key (OpenAI or compatible) | None (Required) | string |
| `CELLMAGE_API_BASE` | API base URL | https://api.openai.com/v1 | string |
| `CELLMAGE_DEFAULT_MODEL` | Default model to use | gpt-4.1-nano | string |
| `CELLMAGE_DEFAULT_PERSONA` | Default persona to use on startup | None | string |

### Resource Directories

| Environment Variable | Description | Default Value | Type |
|---------------------|-------------|--------------|------|
| `CELLMAGE_PERSONAS_DIR` | Primary directory containing persona definitions | ./llm_personas | string |
| `CELLMAGE_PERSONAS_DIRS` | Additional directories to search for personas (comma-separated) | [] | string/list |
| `CELLMAGE_SNIPPETS_DIR` | Primary directory containing snippets | ./llm_snippets | string |
| `CELLMAGE_SNIPPETS_DIRS` | Additional directories to search for snippets (comma-separated) | [] | string/list |
| `CELLMAGE_CONVERSATIONS_DIR` | Directory for saving conversations | ./llm_conversations | string |

### Storage Configuration

| Environment Variable | Description | Default Value | Type |
|---------------------|-------------|--------------|------|
| `CELLMAGE_STORAGE_TYPE` | Storage backend type ('sqlite', 'memory', or 'file') | sqlite | string |
| `CELLMAGE_SQLITE_PATH` | Path to SQLite database | ~/.cellmage/conversations.db | string |
| `CELLMAGE_STORE_RAW_RESPONSES` | Whether to store raw API request/response data | False | boolean |
| `CELLMAGE_AUTO_SAVE` | Whether to automatically save conversations | True | boolean |
| `CELLMAGE_AUTOSAVE_FILE` | Filename for auto-saved conversations | autosaved_conversation | string |

### Model Mapping Configuration

| Environment Variable | Description | Default Value | Type |
|---------------------|-------------|--------------|------|
| `CELLMAGE_MODEL_MAPPINGS_FILE` | Path to YAML file containing model name mappings | None | string |
| `CELLMAGE_AUTO_FIND_MAPPINGS` | Automatically look for cellmage_models.yml in notebook directory | True | boolean |

### Adapter Configuration

| Environment Variable | Description | Default Value | Type |
|---------------------|-------------|--------------|------|
| `CELLMAGE_ADAPTER` | LLM adapter type (direct or langchain) | direct | string |
| `CELLMAGE_AUTO_DISPLAY` | Whether to automatically display chat messages | True | boolean |

### Logging Configuration

| Environment Variable | Description | Default Value | Type |
|---------------------|-------------|--------------|------|
| `CELLMAGE_LOG_LEVEL` | Global logging level | INFO | string |
| `CELLMAGE_CONSOLE_LOG_LEVEL` | Console logging level | WARNING | string |
| `CELLMAGE_LOG_FILE` | Log file path | cellmage.log | string |

## 🌐 Service-Specific Configuration

### Jira Integration

```ini
JIRA_URL=https://your-company.atlassian.net
JIRA_USER_EMAIL=your.email@company.com
JIRA_API_TOKEN=your_jira_api_token
```

### Confluence Integration

```ini
CONFLUENCE_URL=https://your-company.atlassian.net/wiki
# Confluence uses Jira credentials
JIRA_USER_EMAIL=your.email@company.com
JIRA_API_TOKEN=your_jira_api_token
```

### GitHub Integration

```ini
GITHUB_TOKEN=your_github_personal_access_token
```

### GitLab Integration

```ini
GITLAB_URL=https://gitlab.com
GITLAB_PAT=your_gitlab_personal_access_token
# Or alternatively:
GITLAB_PRIVATE_TOKEN=your_gitlab_personal_access_token
```

### Google Docs Integration

```ini
# OAuth configuration (default)
CELLMAGE_GDOCS_AUTH_TYPE=oauth
CELLMAGE_GDOCS_TOKEN_PATH=~/.cellmage/gdocs_token.pickle
CELLMAGE_GDOCS_CREDENTIALS_PATH=~/.cellmage/gdocs_credentials.json

# Or service account configuration
CELLMAGE_GDOCS_AUTH_TYPE=service_account
CELLMAGE_GDOCS_SERVICE_ACCOUNT_PATH=~/.cellmage/gdocs_service_account.json

# Optional: Override the scopes (comma-separated)
CELLMAGE_GDOCS_SCOPES=https://www.googleapis.com/auth/documents.readonly
```

## 🔒 Custom Headers

CellMage supports custom headers for LLM requests using the `CELLMAGE_HEADER_` prefix:

```ini
# Add custom header to LLM requests
CELLMAGE_HEADER_X_MY_CUSTOM_HEADER=my_value
# Will send header: x-my-custom-header: my_value

# Example: Allow certain entity types in redaction services
CELLMAGE_HEADER_X_REDACT_ALLOW=LOCATION,PERSON
```

Header names are automatically converted from environment variable format to proper HTTP header format (lowercase with hyphens instead of underscores).

## 📁 Directory Handling

For `CELLMAGE_PERSONAS_DIRS` and `CELLMAGE_SNIPPETS_DIRS`, you can specify multiple directories using commas or semicolons:

```bash
# Comma-separated example
export CELLMAGE_PERSONAS_DIRS="~/global_personas,./project_personas,/shared/team_personas"

# Semicolon-separated example (useful in Windows environments)
export CELLMAGE_PERSONAS_DIRS="~/global_personas;./project_personas;/shared/team_personas"
```

CellMage will automatically search all specified directories when looking for personas or snippets.

## 💡 Tips and Best Practices

1. **Sensitive Information**: Keep API keys in environment variables or `.env` files, never hardcode them in notebooks
2. **Project-Specific Settings**: Use `.env` files for project-specific settings
3. **Runtime Adjustments**: Use `%llm_config` for temporary changes during a session
4. **Check Status**: Use `%llm_config --status` to verify your current configuration
5. **Custom Model Aliases**: Create short aliases for your frequently used models in `cellmage_models.yml`
6. **Multi-Directory Setup**: For team environments, consider using a combination of global, team, and project-specific directories for personas and snippets

## 🔄 Runtime Configuration with `%llm_config`

The `%llm_config` magic command provides a flexible way to configure CellMage during a session without modifying environment variables or `.env` files. Here are some common use cases:

```ipython
# View current configuration
%llm_config --status

# Change the model for the session
%llm_config --model gpt-4o

# Switch to a different persona
%llm_config --persona code_expert

# Set parameter overrides
%llm_config --set-override temperature 0.7
%llm_config --set-override max_tokens 1000

# Clear all overrides
%llm_config --clear-overrides

# Enable auto-saving
%llm_config --auto-save

# View model name mappings
%llm_config --list-mappings

# Add a new model alias
%llm_config --add-mapping g4t gpt-4-turbo
```

For a complete reference of all available `%llm_config` options, see the [Magic Commands](./magic_commands.md) documentation.
