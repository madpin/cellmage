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

Set up your magical environment by configuring your API keys:

```bash
# Using environment variables
export CELLMAGE_API_KEY="your_openai_api_key"
export CELLMAGE_DEFAULT_MODEL="gpt-4o"

# Or create a .env file in your working directory
echo "CELLMAGE_API_KEY=your_openai_api_key" > .env
echo "CELLMAGE_DEFAULT_MODEL=gpt-4o" >> .env
```

## 🪄 Your First Incantation

Let's verify that your CellMage installation is working properly:

```python
# In your Jupyter Notebook
%load_ext cellmage.integrations.ipython_magic

# Check status
%llm_config --status

# Cast your first spell!
%%llm
Tell me a fun fact about wizards in computing history.
```

If your spell works, congratulations! You're now ready to explore the full magical potential of CellMage.

🎩✨ **Let the wizardry begin!** ✨🎩
