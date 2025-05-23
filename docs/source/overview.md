# 🧙 Overview: Unleash Your LLM Superpowers

## 🪄 What is CellMage?

CellMage is your magical companion for Jupyter notebooks, transforming ordinary code cells into powerful LLM interactions! Think of it as having an AI wizard 🧙‍♂️ sitting right next to you while you code, ready to assist whenever you summon it.

Under the hood, CellMage consists of several powerful magical components working together:

- **🧠 ChatManager**: The central orchestrator that handles LLM interactions and manages the conversation flow
- **📜 HistoryManager**: (Deprecated) Previously kept track of your conversation history and managed message persistence. Use **ConversationManager** instead.
- **🎭 Personas**: Predefined AI personalities with specific system prompts and parameters
- **📋 Snippets**: Reusable context blocks that can be injected into conversations
- **🔌 Adapters**: Connects to different LLM providers (OpenAI, compatible APIs, and more)
- **💾 Storage**: Saves your conversations using SQLite (default) or Markdown files for easy reference
- **🧩 Integrations**: Links CellMage to external tools like Jira, GitHub, GitLab, and Confluence

All these components work seamlessly together to create a frictionless LLM experience in your notebook environment.

## ✨ A Sprinkle of Magic Dust

With CellMage, you can:

- 💬 Chat with sophisticated AI models using simple `%%llm` magic commands
- 🎭 Switch between different AI personalities (personas) with a flick of your wand
- 🔮 Turn your entire notebook into an AI chat interface with Ambient Mode
- 📚 Save your magical conversations for later reference
- 🧩 Connect to external knowledge sources like GitHub, GitLab, Jira, and Confluence
- ⚡ Execute Python code generated by the LLM right in your notebook

## 🚀 Getting Started in 10 Seconds

```text
# Install the magic
!pip install cellmage

# Load the extension
%load_ext cellmage

# Cast your first spell!
%%llm
Tell me a fun fact about wizards in computing history.
```

## 🎯 Perfect For...

- 🧪 Data scientists exploring datasets with AI assistance
- 💻 Developers getting code explanations and suggestions
- 📝 Writers crafting documentation with AI help
- 🎓 Students learning new concepts interactively
- 🔍 Researchers analyzing complex information
- ⚙️ Automating repetitive LLM tasks in data workflows

Ready to start your magical journey? Check out the [Magic Commands](magic_commands.md) to learn all the spells in your new wizard toolkit!
