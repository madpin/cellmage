# 🧙‍♂️ Summoning CellMage

## ✨ Magical Requirements

Before you can summon the CellMage to assist you, ensure you have the following magical components:

- 🐍 Python 3.8 or later
- 🔮 Jupyter Notebook or JupyterLab environment
- 📜 An API key for your chosen LLM service (e.g., OpenAI)

## 🪄 Quick Installation Spell

The simplest way to install CellMage is through the mystical PyPI repository:

```bash
pip install cellmage
```

## 🧪 Optional Potion Ingredients

CellMage offers various magical extensions to enhance your experience. Install them with:

```bash
# For all integrations (recommended for wizards who want the full experience)
pip install "cellmage[all]"

# For specific integrations
pip install "cellmage[github]"      # GitHub integration
pip install "cellmage[gitlab]"      # GitLab integration
pip install "cellmage[jira]"        # Jira integration
pip install "cellmage[confluence]"  # Confluence integration
pip install "cellmage[langchain]"   # LangChain adapter support
```

## 🧩 Developer Enchantments

If you're a wizard looking to contribute to CellMage:

```bash
# Clone the repository
git clone https://github.com/madpin/cellmage.git
cd cellmage

# Create a magical environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install for development
pip install -e ".[dev,all]"
```

## ⚡ Configuration Charm

### 🔑 Essential API Keys

CellMage requires an API key to communicate with your LLM service provider. This is the most important configuration step:

```bash
# Using environment variables (recommended for security)
export CELLMAGE_API_KEY="your_openai_api_key"
# OR use OPENAI_API_KEY if you prefer
export OPENAI_API_KEY="your_openai_api_key"
```

### 📄 Using .env Files

CellMage automatically reads from a `.env` file in your working directory, which is a convenient way to set configuration without exposing sensitive information:

```bash
# Create a .env file with your configuration
cat > .env << EOF
# Essential configuration
CELLMAGE_API_KEY=your_openai_api_key
CELLMAGE_DEFAULT_MODEL=gpt-4o
CELLMAGE_API_BASE=https://api.openai.com/v1

# Optional: Storage configuration
CELLMAGE_SQLITE_PATH=~/.cellmage/conversations.db
CELLMAGE_PERSONAS_DIRS=~/my_personas,./project_personas
CELLMAGE_SNIPPETS_DIRS=~/my_snippets,./project_snippets
EOF
```

### 🔮 Environment Variables Reference

#### Essential Variables
| Environment Variable | Description | Default Value |
|---------------------|-------------|--------------|
| `CELLMAGE_API_KEY` or `OPENAI_API_KEY` | Your LLM API key | None (Required) |
| `CELLMAGE_API_BASE` | API base URL | https://api.openai.com/v1 |
| `CELLMAGE_DEFAULT_MODEL` | Default model to use | gpt-4o-mini |

#### Storage Variables
| Environment Variable | Description | Default Value |
|---------------------|-------------|--------------|
| `CELLMAGE_PERSONAS_DIRS` | Comma-separated list of directories containing personas | ./llm_personas |
| `CELLMAGE_SNIPPETS_DIRS` | Comma-separated list of directories containing snippets | ./llm_snippets |
| `CELLMAGE_CONVERSATIONS_DIR` | Directory for saving conversations | ./llm_conversations |
| `CELLMAGE_SQLITE_PATH` | Path to SQLite database | ~/.cellmage/conversations.db |
| `CELLMAGE_ADAPTER` | LLM adapter type (direct or langchain) | direct |
| `CELLMAGE_STORAGE_TYPE` | Storage type to use (sqlite, memory, file) | sqlite |

#### Integration Variables
| Service | Required Environment Variables |
|---------|----------------------------|
| **Jira** | `JIRA_URL`, `JIRA_USER_EMAIL`, `JIRA_API_TOKEN` |
| **Confluence** | `CONFLUENCE_URL` (or `JIRA_URL`), `JIRA_USER_EMAIL`, `JIRA_API_TOKEN` |
| **GitHub** | `GITHUB_TOKEN` |
| **GitLab** | `GITLAB_URL`, `GITLAB_PAT` or `GITLAB_PRIVATE_TOKEN` |
| **Google Docs** | `CELLMAGE_GDOCS_AUTH_TYPE`, `CELLMAGE_GDOCS_TOKEN_PATH`, `CELLMAGE_GDOCS_CREDENTIALS_PATH` (for OAuth) or `CELLMAGE_GDOCS_SERVICE_ACCOUNT_PATH` (for service account) |

### 📚 Model Aliasing

CellMage supports model aliasing to create shortcuts for model names. You can define aliases in a `cellmage_models.yml` file in your working directory:

```yaml
# Example cellmage_models.yml
mappings:
  gpt4: gpt-4o
  gpt4-mini: gpt-4o-mini
  gpt3: gpt-3.5-turbo
```

A reference example can be found in `cellmage/examples/cellmage_models.yml`. This allows you to use shorter aliases like `%llm_config --model gpt4` instead of full model names.

## 🪄 Your First Incantation

Let's verify that your CellMage installation is working properly:

```ipython
# In your Jupyter Notebook
%load_ext cellmage

# Check status
%llm_config --status

# Cast your first spell!
%%llm
Tell me a fun fact about wizards in computing history.
```

If your spell works, congratulations! You're now ready to explore the full magical potential of CellMage.

🎩✨ **Let the wizardry begin!** ✨🎩
