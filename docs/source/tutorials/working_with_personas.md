# 🎭 Crafting Your Own Spells: Creating Custom Personas

Personas are one of CellMage's most powerful features, allowing you to shape how the LLM behaves by providing tailored system instructions and default parameters. This tutorial will guide you through creating and using custom personas.

## 🧩 What is a Persona?

A persona in CellMage consists of:
1. **System Instructions**: Guidance for how the LLM should behave
2. **Default Parameters**: Model settings like temperature, model name, etc.
3. **Metadata**: Name, description, and other information about the persona

Personas allow you to quickly switch between different LLM "personalities" optimized for different tasks without rewriting your prompts each time.

## 📂 Persona File Structure

Personas are stored as Markdown files with YAML frontmatter. The frontmatter contains the metadata and parameters, and the Markdown body contains the system instructions.

Here's a basic example:

```markdown
---
name: Python Expert
model: gpt-4o
temperature: 0.3
description: An expert Python developer who provides clear, optimized code examples.
---
You are an expert Python developer with deep knowledge of the language, its standard library, and best practices.

When asked coding questions, provide clean, well-commented, PEP 8 compliant solutions.
Always consider edge cases, performance, and readability.
Explain your reasoning and offer suggestions for improvements.
```

## 🗂️ Persona Directory Structure

By default, CellMage looks for personas in a directory called `llm_personas` in your working directory. You can also specify additional directories using the `CELLMAGE_PERSONAS_DIR` and `CELLMAGE_PERSONAS_DIRS` environment variables.

```bash
# Setting up a personas directory structure
mkdir -p llm_personas
mkdir -p ~/global_personas  # For personas you want available in all projects
```

```ini
# In your .env file
CELLMAGE_PERSONAS_DIRS=~/global_personas,./project_specific_personas
```

## ✨ Creating Your First Custom Persona

Let's create a simple data analyst persona:

```ipython
# First, create the personas directory if it doesn't exist
!mkdir -p llm_personas
```

Now create the file `llm_personas/data_analyst.md`:

```markdown
---
name: Data Analyst
model: gpt-4o
temperature: 0.2
max_tokens: 1000
description: A data analyst focused on insights and visualization recommendations.
---
You are an experienced data analyst with expertise in statistics, data visualization, and insights generation.

When presented with data or data-related questions:
1. Focus on extracting meaningful insights rather than just describing the data
2. Recommend appropriate visualization techniques when relevant
3. Consider statistical validity and potential biases
4. Suggest follow-up analyses that might yield additional insights
5. Use clear language that non-technical stakeholders can understand

Avoid making unfounded claims about causality unless explicitly supported by the data.
```

## 🧪 Testing Your Persona

Let's use our new persona:

```ipython
# Load the CellMage extension if you haven't already
%load_ext cellmage.integrations.ipython_magic

# List available personas to confirm yours is detected
%llm_config --list-personas

# Activate your persona
%llm_config --persona data_analyst

# Try it out!
%%llm
I have a dataset of customer purchases with columns for customer_id,
purchase_date, product_category, and purchase_amount.
What insights might I look for and how should I visualize them?
```

## 🔧 Advanced Persona Features

### Persona Parameter Reference

The YAML frontmatter can include:

| Parameter | Description | Example Value |
|-----------|-------------|---------------|
| `name` | Display name of the persona | `"Python Expert"` |
| `description` | Brief description | `"An expert Python developer..."` |
| `model` | Default model to use | `"gpt-4o"` |
| `temperature` | Creativity level (0.0-2.0) | `0.7` |
| `max_tokens` | Maximum response length | `1000` |
| `top_p` | Nucleus sampling parameter | `0.9` |
| `frequency_penalty` | Repetition reduction (0.0-2.0) | `0.0` |
| `presence_penalty` | Topic diversity (0.0-2.0) | `0.0` |
| `stop` | Stop sequences | `["\n\n", "END"]` |

### Creating Specialized Personas

Here are some ideas for specialized personas:

#### Code Reviewer

```markdown
---
name: Code Reviewer
model: gpt-4o
temperature: 0.2
description: Analyzes code for bugs, style issues, and optimizations.
---
You are an expert code reviewer with deep knowledge of software engineering principles.

When reviewing code:
1. Identify potential bugs, edge cases, and error handling issues
2. Point out style inconsistencies and readability problems
3. Suggest performance optimizations when appropriate
4. Look for security vulnerabilities
5. Be constructive and specific in your feedback

Organize your review by issue severity (critical, major, minor).
Include code snippets showing improved implementations when possible.
```

#### Creative Writer

```markdown
---
name: Creative Writer
model: gpt-4o
temperature: 0.9
max_tokens: 1500
description: Writes creative fiction with vivid imagery.
---
You are a creative fiction writer with a talent for vivid imagery and compelling storytelling.

When writing fiction:
1. Focus on sensory details and immersive description
2. Create interesting, nuanced characters with believable motivations
3. Balance dialogue, narration, and description
4. Use varied sentence structure and pacing for emotional effect
5. Maintain a consistent tone and point of view

Adapt your style to match the requested genre while maintaining high quality prose.
```

## 💡 Tips for Effective Personas

1. **Be Specific**: The more specific your instructions, the more consistent the persona's behavior.
2. **Use Examples**: Include examples of desired outputs in your system instructions.
3. **Set Boundaries**: Clearly define what the persona should and shouldn't do.
4. **Match Parameters to Purpose**: Use lower temperature for factual tasks, higher for creative ones.
5. **Iterative Refinement**: If your persona isn't behaving as expected, refine the instructions based on actual outputs.

## 🔀 Switching Between Personas

You can easily switch between personas during a session:

```python
# Switch to the data analyst
%llm_config --persona data_analyst

# Later, switch to a code reviewer
%llm_config --persona code_reviewer

# And if needed, use a one-time persona just for the next prompt
%%llm -p creative_writer
Write a short story about a data scientist who discovers magic in their code.
```

## 🧠 Understanding the Current Persona

To see which persona is active and what its system instructions are:

```python
# Show the current persona
%llm_config --show-persona
```

## 🚀 Next Steps

Now that you've learned how to create and use custom personas, explore:
- [Using Snippets](using_snippets.md): Learn how to provide reusable context blocks
- [Advanced Prompting](advanced_prompting.md): Combine personas with advanced prompting techniques
- [Managing Conversations](conversation_management.md): Save and manage sessions with different personas
