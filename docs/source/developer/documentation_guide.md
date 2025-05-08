# 📝 Documentation Guide

This guide explains how to write documentation for CellMage, with a focus on code examples and formatting.

## 🧩 Markdown Structure

CellMage documentation uses MyST Markdown, which is an extension of standard Markdown with additional features for technical documentation.

### Headers Structure

- `# Level 1` - Top-level page title
- `## Level 2` - Major sections
- `### Level 3` - Subsections
- `#### Level 4` - Additional headings as needed

## 📊 Code Blocks and Examples

When including code examples:

### For IPython/Magic Command Examples

```ipython
%%llm
What is the capital of France?
```

Notice that we're using the `ipython` language specifier above, not `python`. This is critical for all code blocks containing:

- Magic commands (`%llm_config`, `%%llm`, etc.)
- Question marks in prompts
- Dollar signs (e.g., in financial examples)
- Exclamation marks for shell commands
- Triple backtick code blocks within code blocks

### For Regular Python Code

```ipython
def calculate_metrics(data):
    """Calculate basic statistics on the data."""
    return {
        "mean": sum(data) / len(data),
        "max": max(data),
        "min": min(data)
    }
```

### For Shell Commands

```bash
pip install cellmage
```

## 🎭 Including Personas and Snippets Examples

When documenting the creation of persona or snippet files:

````md
Create a file `llm_personas/data_analyst.md`:

```markdown
---
name: Data Analyst
model: gpt-4o
temperature: 0.3
---
You are a data analyst expert who specializes in interpreting data, finding patterns,
and creating visualizations to communicate insights.
```
````

## 🔄 Cross-References and Links

To refer to other pages in the documentation:

```md
See [Magic Commands](../magic_commands.md) for more details.
```

For external links:

```md
Visit the [GitHub repository](https://github.com/madpin/cellmage).
```

## 🖼️ Including Images

To include images:

```md
![CellMage Workflow](../_static/images/cellmage_workflow.png)
```

## 📋 Tables

Tables are created with pipe syntax:

```md
| Parameter | Description | Default |
|-----------|-------------|---------|
| `model` | The LLM model to use | `gpt-4o-mini` |
| `temperature` | Creativity setting | 0.7 |
```

## 🧠 Tips for Clear Documentation

1. **Start with a clear introduction** - Explain what the page covers and who it's for.
2. **Use consistent terminology** - Stick to the same terms throughout.
3. **Progressive disclosure** - Start with simple examples, then show more complex ones.
4. **Show real-world use cases** - Demonstrate practical applications.
5. **Include error handling** - Show what happens when things go wrong.
6. **Use callouts for important notes** - Highlight key information.

### Callout Example

> **⚠️ Warning:** Make sure you have set your API key before running this command.

## 🔄 Fixing Lexer Errors in Documentation

If you encounter syntax highlighting errors when building the documentation:

1. For code blocks with CellMage magic commands, use `ipython` instead of `python`:
   ````md
   ```ipython
   %%llm
   What is the capital of France?
   ```
   ````

2. For nested code blocks (code inside code examples), add an extra level of backticks:

   `````md
   ````ipython
   %%llm
   ```ipython
   def example():
       return "This is nested code"
   ```
   ````
   `````

3. If you still encounter errors, consider using plain text blocks that don't attempt syntax highlighting:
   ````md
   ```text
   %llm_config --model gpt-4o
   ```
   ````

### Common Symbols Causing Lexer Errors

The following characters/symbols often cause lexer errors in Python code blocks but work correctly with `ipython` language specifier:

| Symbol | Example | Solution |
|--------|---------|----------|
| Question marks (`?`) | `%%llm What is the capital of France?` | Use `ipython` language |
| Dollar signs (`$`) | `Price: $25.99` | Use `ipython` language |
| Exclamation marks (`!`) | `!pip install cellmage` | Use `ipython` language |
| Triple backticks (`` ``` ``) | Code blocks inside prompts | Add extra backtick level |
| Mathematical symbols (`²`, `π`) | `O(n²)` complexity | Use `ipython` or `text` |

### Adding Code Examples to Documentation

When adding example code blocks to tutorials:

1. **For magic commands and prompts with questions:**
   ````md
   ```ipython
   %%llm
   Compare the advantages of SQL and NoSQL databases?
   ```
   ````

2. **For shell commands in IPython:**
   ````md
   ```ipython
   !mkdir -p llm_snippets
   !pip install "cellmage[all]"
   ```
   ````

3. **For data that contains special characters:**
   ````md
   ```ipython
   %%llm
   The price dropped from $50 to $42.50. What's the percentage decrease?
   ```
   ````

### Including Documentation in TOC

Make sure your documentation files are included in a table of contents (toctree) in an appropriate parent file. For example, to include this guide in the developer documentation toctree, add it to `docs/source/developer/index.md`:

```md
```{toctree}
:maxdepth: 2
documentation_guide
```
```
