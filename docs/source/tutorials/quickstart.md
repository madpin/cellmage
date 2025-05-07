# 🚀 Your First Magical Interaction: A Guided Tour

Welcome to your first CellMage adventure! This guided tour will take you from installation to your first meaningful LLM interaction in just a few minutes.

## 🧙‍♂️ Step 1: Summoning CellMage

First, let's make sure CellMage is installed and ready to use:

```bash
# Install CellMage with all its magical capabilities
pip install "cellmage[all]"

# Or for a minimal installation
pip install cellmage
```

## 🔑 Step 2: Preparing Your Magical Key

CellMage needs an API key to communicate with LLM services. Let's set that up:

```bash
# Set your API key in your environment (recommended)
export CELLMAGE_API_KEY="your_openai_api_key"

# Alternatively, create a .env file in your working directory
echo "CELLMAGE_API_KEY=your_openai_api_key" > .env
```

## 🧪 Step 3: Starting a New Notebook

Open a new Jupyter notebook and let's get started. You'll first need to load the CellMage extension:

```python
# Load the CellMage magical extension
%load_ext cellmage.integrations.ipython_magic

# Let's check that everything is working correctly
%llm_config --status
```

You should see a status message showing your current configuration, including the default model, whether any personas are active, and if there are any parameter overrides.

## ✨ Step 4: Your First Spell

Let's cast your first spell by sending a prompt to your LLM:

```python
%%llm
Explain what large language models are in 3 simple sentences.
```

Within moments, you should see a response appear below the cell, along with some stats about the interaction:
- ⏱️ How long the response took
- 📊 Token usage (input and output)
- 💰 Estimated cost of the request
- 🤖 Which model was used

## 🎛️ Step 5: Adjusting the Magic

Let's try tweaking some parameters to see how they affect the response:

```python
%%llm --temperature 0.8 --model gpt-4o
Write a short, imaginative story about a wizard who uses AI to help with spellcasting.
```

The `--temperature` parameter increases creativity, and we've also specified a different model for this request.

## 🎭 Step 6: Using a Different Persona

CellMage comes with several built-in personas that shape how the LLM responds:

```python
# List available personas
%llm_config --list-personas

# Try using the Python expert persona
%llm_config --persona code_expert

%%llm
What's the best way to handle exceptions in Python?
```

Notice how the LLM's response is now tailored toward coding expertise!

## 🧠 Step 7: Managing Context

CellMage maintains conversation history automatically. Let's see it in action:

```python
%%llm
In your previous response about Python exceptions, can you provide a specific example?
```

The LLM remembers the previous conversation about exceptions and builds on it.

If you want to start fresh:

```python
# Clear the conversation history
%llm_config --clear-history

# Start a new topic
%%llm
What are the key principles of good data visualization?
```

## 🔍 Step 8: Checking Your Stats

Let's see what we've done in this session:

```python
# Show your conversation history
%llm_config --show-history
```

This displays all the messages exchanged in your current session.

## 💾 Step 9: Saving Your Work

Before ending our tour, let's save this conversation:

```python
# Save the conversation with a meaningful name
%llm_config --save "my_first_cellmage_session"
```

You can reload this session later with:

```python
# List saved sessions
%llm_config --list-sessions

# Load a specific session
%llm_config --load "my_first_cellmage_session_20250507_..."
```

## 🎉 Congratulations!

You've completed your first magical tour with CellMage! You now know:
- How to set up and configure CellMage
- How to send basic prompts
- How to adjust parameters like temperature and model
- How to use personas
- How to manage conversation history
- How to save and load sessions

## 🧙‍♂️ Next Steps

Now that you've mastered the basics, explore these next tutorials:
- [Managing Conversations](conversation_management.md) - Learn more about saving, loading, and searching chats
- [Crafting Your Own Personas](working_with_personas.md) - Create custom personas
- [Using Snippets](using_snippets.md) - Reuse content across your prompts

Happy magical journeying with CellMage! ✨
