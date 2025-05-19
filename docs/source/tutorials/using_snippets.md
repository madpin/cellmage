# 📋 Using Snippets: Reusable Context Blocks

Snippets are a powerful feature in CellMage that allow you to inject reusable content into your LLM conversations. This tutorial will show you how to create and use snippets effectively.

## 🧩 What are Snippets?

Snippets are text files containing code, documentation, instructions, or any other content that you want to provide as context to your LLM. Unlike personas (which define the LLM's behavior), snippets provide information that the LLM can reference or analyze in its responses.

Common uses for snippets include:
- Providing code examples for the LLM to analyze
- Including documentation that the LLM should reference
- Sharing project-specific context for consistent responses
- Giving the LLM access to data structures or schemas

## 📂 Snippet Directory Structure

By default, CellMage looks for snippets in a directory called `llm_snippets` under your base directory. You can control the base directory for all working files (including snippets) using the `CELLMAGE_BASE_DIR` environment variable:

```bash
# Set the base directory for all CellMage working files
export CELLMAGE_BASE_DIR=/path/to/your/project
```

Snippets will then be stored in `$CELLMAGE_BASE_DIR/llm_snippets`.

You can also specify additional snippet directories using the `CELLMAGE_SNIPPETS_DIR` and `CELLMAGE_SNIPPETS_DIRS` environment variables (these paths can be absolute or relative to the base directory).

```ini
# In your .env file
CELLMAGE_SNIPPETS_DIRS=~/global_snippets,./project_specific_snippets
```

## ✨ Creating Your First Snippets

Let's create two simple snippets: a Python utility function and a project description.

```ipython
# First, create the snippets directory if it doesn't exist
!mkdir -p $CELLMAGE_BASE_DIR/llm_snippets
```

### Python Utility Function Snippet

Create the file `$CELLMAGE_BASE_DIR/llm_snippets/data_utils.py`:

```ipython
def calculate_metrics(data_series):
    """
    Calculate common statistical metrics for a numeric data series.

    Args:
        data_series (list or array-like): Numeric data

    Returns:
        dict: Dictionary containing calculated metrics
    """
    import numpy as np
    from scipy import stats

    return {
        "count": len(data_series),
        "mean": np.mean(data_series),
        "median": np.median(data_series),
        "std_dev": np.std(data_series),
        "min": np.min(data_series),
        "max": np.max(data_series),
        "quartiles": np.percentile(data_series, [25, 50, 75]),
        "skewness": stats.skew(data_series),
        "kurtosis": stats.kurtosis(data_series)
    }

def detect_outliers(data_series, method="iqr", threshold=1.5):
    """
    Detect outliers in a data series using specified method.

    Args:
        data_series (list or array-like): Numeric data
        method (str): Method to use ("iqr" or "zscore")
        threshold (float): Threshold for outlier detection

    Returns:
        tuple: (outlier_indices, outlier_values)
    """
    import numpy as np

    if method == "iqr":
        q1, q3 = np.percentile(data_series, [25, 75])
        iqr = q3 - q1
        lower_bound = q1 - (threshold * iqr)
        upper_bound = q3 + (threshold * iqr)
        outlier_indices = np.where((data_series < lower_bound) | (data_series > upper_bound))[0]
    elif method == "zscore":
        z_scores = (data_series - np.mean(data_series)) / np.std(data_series)
        outlier_indices = np.where(np.abs(z_scores) > threshold)[0]
    else:
        raise ValueError(f"Unknown method: {method}")

    outlier_values = [data_series[i] for i in outlier_indices]
    return outlier_indices, outlier_values
```

### Project Description Snippet

Create the file `$CELLMAGE_BASE_DIR/llm_snippets/project_description.md`:

```markdown
# Customer Analysis Project

## Project Goal
Analyze customer purchase patterns to identify opportunities for targeted marketing campaigns and product recommendations.

## Available Data
- customer_purchases.csv: 10,000 records of customer purchases with columns:
  - customer_id: Unique identifier for each customer
  - purchase_date: Date of purchase (YYYY-MM-DD)
  - product_category: Category of the purchased product
  - product_id: Unique identifier for each product
  - purchase_amount: Amount spent in dollars
  - customer_location: City or region

- customer_demographics.csv: Demographic information with columns:
  - customer_id: Unique identifier matching purchase data
  - age_group: Age range (18-24, 25-34, 35-44, 45-54, 55+)
  - income_bracket: Income level (Low, Medium, High)
  - joined_date: Date when the customer first signed up

## Analysis Requirements
1. Identify purchasing patterns by demographic groups
2. Detect seasonal trends in product categories
3. Find correlations between purchase amount and other factors
4. Generate recommendations for cross-selling opportunities
```

## 🧪 Using Snippets in Your Conversations

There are several ways to use snippets in your conversations:

### 1. Add a Snippet as a User Message

This adds the snippet content as if the user had typed it:

```ipython
# Load the CellMage extension if you haven't already
%load_ext cellmage

# Add the data_utils.py file as context
%llm_config --snippet data_utils.py

# Now ask the LLM about it
%%llm
Review the utility functions I provided. What improvements or additional functions
would you suggest to make this more comprehensive for data analysis?
```

### 2. Documentation Snippets

For technical questions, provide documentation:

```ipython
%%llm --snippet api_documentation.md
How would I implement a function to authenticate with this API and retrieve user data?
```

### 3. Use a Snippet Just for One Call

You can use a snippet just for a single prompt without affecting the overall conversation:

```ipython
%%llm --snippet data_utils.py
Explain how the detect_outliers function works and suggest an additional method
that could be implemented for outlier detection.
```

## 🔄 Managing Snippets in a Session

### Viewing Active Snippets

To see what snippets are currently active:

```ipython
# List current snippets
%llm_config --status
```

The status display will show any currently active snippets.

### Listing Available Snippets

To see all available snippets:

```ipython
# List all available snippets
%llm_config --list-snippets
```

### Removing Snippets

To remove an active snippet:

```ipython
# Remove a specific snippet
%llm_config --remove-snippet data_utils.py

# Remove all snippets
%llm_config --clear-snippets
```

## 💡 Effective Snippet Strategies

### 1. Code Context Snippets

When asking LLMs to help with code, provide relevant files:

```ipython
%%llm --snippet my_module.py --snippet test_module.py
I'm seeing a bug where the function fails when given empty input. How can I fix it?
```

### 2. Documentation Snippets

For technical questions, provide documentation:

```ipython
%%llm --snippet api_documentation.md
How would I implement a function to authenticate with this API and retrieve user data?
```

### 3. Data Schema Snippets

When discussing databases, provide schema information:

```ipython
%%llm --snippet database_schema.sql
Write a query to find customers who purchased more than 5 items in the last month,
including their contact information and total spend.
```

### 4. Project Context Snippets

Keep the LLM informed about your project:

```ipython
%%llm --sys-snippet project_goals.md
Given our project goals, what metrics should we track to measure success?
```

## 📄 Snippet Best Practices

1. **Keep snippets focused**: Each snippet should serve a specific purpose
2. **Use descriptive filenames**: Make it easy to remember what each snippet contains
3. **Update snippets regularly**: Keep them in sync with your project's evolution
4. **Use the right format**: Choose the right file extension (.py, .md, .sql, etc.) for syntax highlighting
5. **Combine with personas**: Use snippets with appropriate personas for the best results

## 🧠 Snippets + Personas: Powerful Combinations

Combining snippets with personas creates powerful workflows:

```ipython
# Load a code reviewer persona
%llm_config --persona code_reviewer

# Add your code as context
%llm_config --snippet my_algorithm.py

# Get a code review
%%llm
Please review this code for performance issues and security vulnerabilities.
```

## 🚀 Next Steps

Now that you've learned how to use snippets effectively, explore:
- [Code Review with CellMage](github_code_review.md): Learn how to integrate with GitHub/GitLab
- [Advanced Prompting](advanced_prompting.md): Combine snippets with advanced prompting techniques
- [Chain of Thought](chain_of_thought.md): Use snippets for complex reasoning tasks
