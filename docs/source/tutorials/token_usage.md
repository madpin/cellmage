# 🪙 Understanding Token Usage and Costs

When working with LLMs in CellMage, it's important to understand how tokens work, how they affect your costs, and how to optimize your usage. This tutorial will help you master these concepts.

## 📊 What are Tokens?

Tokens are the basic units of text that LLMs process. A token can be as short as a single character or as long as a full word, depending on the tokenization algorithm used.

As a rough approximation for English text:
- 1 token ≈ 4 characters
- 1 token ≈ 3/4 of a word
- 100 tokens ≈ 75 words

Different languages and technical content may have different token densities.

## 💰 How CellMage Tracks Tokens and Costs

CellMage automatically tracks token usage for each conversation and displays it after each LLM interaction:

```
✅ (⏱️ 2.3s) (📥 142 tokens, 📤 318 tokens) (🪙 $0.0023) [gpt-4o-mini]
```

This status line shows:
- ✅ Success indicator
- ⏱️ Time taken for the response
- 📥 Input tokens (what you sent to the LLM)
- 📤 Output tokens (what the LLM returned)
- 🪙 Estimated cost
- Model used in brackets

You can also view token usage for your entire conversation:

```python
# Show conversation history with token counts
%llm_config --show-history
```

## 💸 How Token Costs are Calculated

Different models have different pricing structures, typically charging separately for input and output tokens:

| Model | Input Cost (per 1K tokens) | Output Cost (per 1K tokens) |
|-------|----------------------------|----------------------------|
| GPT-3.5-Turbo | $0.0005 | $0.0015 |
| GPT-4o-mini | $0.0015 | $0.0020 |
| GPT-4o | $0.005 | $0.015 |
| GPT-4 Turbo | $0.01 | $0.03 |
| Claude 3 Haiku | $0.00025 | $0.00125 |
| Claude 3 Sonnet | $0.003 | $0.015 |

*Note: Prices as of May 2025. Check provider websites for the most current pricing.*

CellMage uses these rates to calculate the estimated cost of each interaction.

## 🔍 Practical Token Usage Examples

Let's look at some practical examples to understand token usage in context:

### Example 1: Simple Question and Answer

```python
%%llm
What is the capital of France?
```

Approximate tokens:
- Input: 7 tokens
- Output: 10-20 tokens
- Total cost (GPT-4o): ~$0.0004

### Example 2: Code Review

```python
%%llm --snippet my_function.py
Review this code for bugs and efficiency improvements.
```

If `my_function.py` contains 100 lines of code:
- Input: ~700-1000 tokens
- Output: ~500-1000 tokens
- Total cost (GPT-4o): ~$0.01-0.02

### Example 3: GitHub Repository Analysis

```python
%github username/medium-project
%%llm
Analyze this repository architecture.
```

For a medium-sized repository:
- Input: ~5000-15000 tokens
- Output: ~1000-2000 tokens
- Total cost (GPT-4o): ~$0.04-0.10

## 🧪 Exploring with the Token Counting Example

CellMage includes a token counting example to help you understand how different texts are tokenized:

```python
# Run the token counting example script
!python examples/token_counting_example.py
```

You can also tokenize custom text:

```python
from cellmage.utils.token_utils import estimate_tokens

# Estimate tokens in a simple string
text = "This is a sample text for token counting demonstration."
print(f"Estimated tokens: {estimate_tokens(text)}")

# Estimate tokens in a code file
with open('my_script.py', 'r') as f:
    code = f.read()
    print(f"Estimated tokens in code file: {estimate_tokens(code)}")
```

## 📏 Token Limits by Model

Each model has a context window limit - the maximum number of combined input and output tokens:

| Model | Context Window (tokens) |
|-------|------------------------|
| GPT-3.5-Turbo | 16,385 |
| GPT-4o-mini | 128,000 |
| GPT-4o | 128,000 |
| GPT-4 Turbo | 128,000 |
| Claude 3 Haiku | 200,000 |
| Claude 3 Sonnet | 200,000 |

*Note: Capabilities as of May 2025. Check provider documentation for the most current information.*

## 🛠️ Strategies for Optimizing Token Usage

### 1. Choose the Right Model

Use more powerful models only when needed:

```python
# For simple questions
%%llm -m gpt-3.5-turbo
What is the difference between a list and a tuple in Python?

# For complex reasoning
%%llm -m gpt-4o
Analyze these architectural tradeoffs between microservices and monolithic design...
```

### 2. Use Focused Prompts

Be concise and specific in your prompts:

```python
# Less efficient prompt (more tokens)
%%llm
I have a CSV file with user data including names, email addresses, signup dates,
and activity metrics. I want to analyze this data to understand user engagement
patterns. The data has some missing values and inconsistencies. Can you help me
clean this data and provide some analysis code?

# More efficient prompt (fewer tokens)
%%llm
Write Python code to:
1. Clean a CSV with user data (handle missing values)
2. Calculate user engagement metrics
3. Visualize engagement patterns
```

### 3. Leverage System Messages Efficiently

System messages persist in context, so use them wisely:

```python
# Set a concise but informative system message
%llm_config --sys-snippet project_context.md

# Now your prompts can be more focused
%%llm
What authentication method should we use for the API?
```

### 4. Clean Repository Imports

When using GitHub or GitLab integration, use the `--clean` flag and exclusion options:

```python
# More efficient repository import
%github username/repository --clean --exclude-dir node_modules --exclude-dir .git --exclude-ext .md
```

### 5. Use Pagination for Large Content

Break down large analyses into smaller chunks:

```python
# First, get a high-level overview
%github username/large-repository --clean
%%llm
Give me a high-level architecture overview of this repository.

# Then, dig into specific components
%github username/large-repository --clean --include-dir src/specific-component
%%llm
Analyze this specific component in detail.
```

### 6. Leverage SQLite Storage for Conversation Continuity

Instead of keeping very long conversations in memory, use SQLite storage and reference previous conversations:

```python
# Load SQLite magic to store conversations
%load_ext cellmage.integrations.sqlite_magic

# Start a new conversation about a specific topic
%sqlite --new
%sqlite --tag current architecture_review

# Later, search for that conversation
%sqlite --search architecture_review
```

## 📈 Monitoring Token Usage

CellMage provides several ways to monitor your token usage:

### Conversation History with Token Counts

```python
# View current conversation history with token counts
%llm_config --show-history
```

### SQLite Storage Statistics

If you're using SQLite storage:

```python
# Get statistics for your conversations
%sqlite --stats
```

### Creating a Token Usage Dashboard

You can create a simple token usage dashboard:

```python
# Load SQLite extension
%load_ext cellmage.integrations.sqlite_magic

# Get statistics
%sqlite --stats

# Analyze usage patterns with Pandas
import pandas as pd
import matplotlib.pyplot as plt
from cellmage.storage.sqlite_store import SQLiteConversationStore

# Connect to your SQLite database
store = SQLiteConversationStore()
conversations = store.list_conversations()

# Extract token usage data
usage_data = []
for conv in conversations:
    token_in = sum(msg.metadata.get('tokens_in', 0) for msg in conv.messages if msg.metadata)
    token_out = sum(msg.metadata.get('tokens_out', 0) for msg in conv.messages if msg.metadata)
    cost = sum(float(msg.metadata.get('cost', 0)) for msg in conv.messages if msg.metadata and msg.metadata.get('cost'))
    usage_data.append({
        'conversation_id': conv.id,
        'date': conv.created_at,
        'tokens_in': token_in,
        'tokens_out': token_out,
        'total_tokens': token_in + token_out,
        'estimated_cost': cost,
        'tag': conv.tag if hasattr(conv, 'tag') else None
    })

# Create DataFrame and visualize
df = pd.DataFrame(usage_data)
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date')

# Plot token usage over time
plt.figure(figsize=(12, 6))
plt.plot(df['date'], df['tokens_in'], label='Input Tokens')
plt.plot(df['date'], df['tokens_out'], label='Output Tokens')
plt.plot(df['date'], df['total_tokens'], label='Total Tokens')
plt.xlabel('Date')
plt.ylabel('Token Count')
plt.title('Token Usage Over Time')
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Plot cost distribution by tag if tags exist
if 'tag' in df.columns and df['tag'].notna().any():
    costs_by_tag = df.groupby('tag')['estimated_cost'].sum().sort_values(ascending=False)
    plt.figure(figsize=(10, 6))
    costs_by_tag.plot(kind='bar')
    plt.xlabel('Tag')
    plt.ylabel('Estimated Cost ($)')
    plt.title('Cost Distribution by Conversation Tag')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
else:
    print("No conversation tags found. Consider tagging your conversations with %sqlite --tag command.")

## 💼 Managing Token Budgets

For professional or team use, you might want to set token budgets:

1. **Track usage by project/task**: Tag conversations appropriately
2. **Set usage thresholds**: Monitor when you're approaching model limits
3. **Choose cost-effective models**: Use the most efficient model for the task
4. **Schedule intensive tasks**: Run token-heavy analyses during off-peak hours

## 🚀 Next Steps

Now that you understand token usage and costs in CellMage, explore:
- [Advanced Configuration](../configuration.md): Fine-tune your CellMage environment
- [SQLite Storage](../sqlite_storage.md): Learn how to effectively manage your LLM conversations
- [Working with Personas](working_with_personas.md): Create specialized personas for different tasks
