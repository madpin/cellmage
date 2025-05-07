# 📚 Confluence Knowledge Base: Integrating Wiki Content with LLMs

Welcome to the Confluence Knowledge Base tutorial! This guide will help you seamlessly integrate your organization's Confluence wiki content into your LLM workflows using CellMage.

## 🎯 What You'll Learn

In this tutorial, you'll discover:
- How to connect CellMage to your Confluence instance
- Techniques for importing wiki pages as context for LLM queries
- Strategies for effectively querying your organization's knowledge base
- Advanced patterns for knowledge extraction and summarization
- Best practices for maintaining security and privacy

## 🧙‍♂️ Prerequisites

Before diving in, make sure:
- You have access to a Confluence instance
- You have proper authentication credentials
- You have CellMage installed with the Confluence integration:
  ```bash
  pip install "cellmage[confluence]"
  ```
- You have CellMage loaded in your notebook:
  ```python
  %load_ext cellmage.integrations.ipython_magic
  ```

## 🔑 Step 1: Setting Up Confluence Integration

First, let's configure CellMage to connect to your Confluence instance:

```python
# Set Confluence credentials (recommended approach is using environment variables)
import os
os.environ["CONFLUENCE_URL"] = "https://your-instance.atlassian.net/wiki"
os.environ["CONFLUENCE_USERNAME"] = "your-email@example.com"
os.environ["CONFLUENCE_API_TOKEN"] = "your-api-token"

# Alternatively, configure directly in the notebook
# (Note: Avoid storing credentials in your notebook for production use)
%confluence_config --url "https://your-instance.atlassian.net/wiki" \
                  --username "your-email@example.com" \
                  --api-token "your-api-token"
```

## 🌐 Step 2: Testing Your Connection

Let's verify that the connection works by listing some spaces:

```python
# List available Confluence spaces
%confluence list-spaces
```

You should see a list of spaces you have access to, such as:

```
Available Confluence Spaces:
1. TEAM - Team Documentation
2. PROJ - Project Documentation
3. HR - Human Resources
...
```

## 📄 Step 3: Importing a Single Wiki Page

To import a specific Confluence page into your LLM context:

```python
# Import a page by title
%confluence "Project Overview"

# Or import a page by ID
%confluence --page-id 123456789

# Ask a question about the imported page
%%llm
Summarize the key points from the Project Overview page.
```

## 🔍 Step 4: Searching and Importing Pages

Find relevant pages based on search terms:

```python
# Search for pages containing "onboarding"
%confluence --search "onboarding"

# Import the first result from the search
%confluence --search "onboarding" --first

# Ask a question about the imported content
%%llm
What are the key steps in our onboarding process?
```

## 📂 Step 5: Working with Spaces

You can also work with entire Confluence spaces:

```python
# List all pages in a specific space
%confluence --space "TEAM" --list

# Import all pages from a space (be careful with token limits!)
%confluence --space "TEAM" --all

# Ask a question spanning the entire space
%%llm
What are the main projects our team is currently working on, based on the wiki content?
```

## 🧩 Step 6: Advanced Content Selection

For more fine-grained control over what content to import:

```python
# Import pages with specific labels
%confluence --labels "documentation,api"

# Import pages updated within a time range
%confluence --updated-after "2024-01-01" --labels "release-notes"

# Import pages by a specific author
%confluence --author "jane.doe"

# Ask about recent changes
%%llm
Summarize the recent API changes documented in our wiki.
```

## 📊 Step 7: Handling Large Content

Confluence wikis can be extensive. Here's how to manage large content:

```python
# Import a page but limit the content size
%confluence "Architecture Overview" --max-tokens 2000

# Extract only specific sections using regex patterns
%confluence "Developer Guide" --extract-pattern "## API Reference(.*?)##"

# Import a page and auto-summarize before adding to context
%confluence "Research Findings" --summarize

# Ask about the focused content
%%llm
Based on the API Reference section, what authentication methods are supported?
```

## 🔄 Step 8: Combining Wiki Content with Other Sources

Confluence content can be used alongside other information sources:

```python
# Import Confluence page
%confluence "Service Architecture"

# Add code context from your local files
%llm_config --snippet api_client.py

# Add context from GitHub repository
%github username/repo --path src/main/

# Now ask a comprehensive question
%%llm
Based on our architecture documentation and the API client implementation,
identify any inconsistencies between documentation and code.
```

## 📝 Step 9: Knowledge-Enhanced Workflows

Use Confluence content to enhance your LLM workflows:

```python
# Import company style guide
%confluence "Brand Style Guide"

# Use the style guide to create content
%%llm
Using our company's brand style guidelines, write a blog post announcing
our new feature X. The post should be approximately 400 words.
```

## 🔒 Step 10: Security and Privacy Considerations

When working with corporate wikis:

```python
# Clear sensitive context after use
%confluence --clear

# Check what Confluence content is in context
%confluence --status

# Use temporary context that doesn't persist
%%llm --confluence "Confidential Project Plan" --temp-context
Summarize the timeline for the confidential project.
```

## 🧪 Advanced Confluence Integration Patterns

### Document-Grounded Question Answering

```python
# Import relevant documentation
%confluence --search "authentication" --top 3

%%llm
A new developer is asking how to implement authentication in our system.
Based strictly on our documentation, provide step-by-step instructions.
If any information is missing from the documentation, identify those gaps.
```

### Knowledge Base Aggregation

```python
# Import pages from different spaces
%confluence --space "ENGINEERING" --labels "architecture"
%confluence --space "PRODUCT" --labels "requirements"

%%llm
Compare our technical architecture with our product requirements.
Identify any areas where our current architecture might not support
upcoming product needs.
```

### Document-Based Reasoning

```python
# Import procedural documentation
%confluence "Incident Response Procedure"

%%llm
Given the following incident scenario:
"The payment service is returning intermittent 500 errors during peak hours"

Apply our incident response procedure to this scenario and outline:
1. The appropriate escalation path
2. Initial diagnostic steps
3. Required communication based on our protocols
4. Next steps for resolution
```

## ⚠️ Limitations and Best Practices

When working with Confluence content, keep in mind:

1. **Token limitations** - Large wikis can easily exceed context windows
2. **Content freshness** - Imported content is a snapshot and may become outdated
3. **Permission boundaries** - CellMage can only access content you have permission to view
4. **Security considerations** - Be careful with sensitive information
5. **Formatting loss** - Some rich formatting and macros may not import perfectly

## 🚀 Best Practices

- **Be specific** - Target exactly the pages you need
- **Use labels strategically** - Encourage your team to label Confluence pages consistently
- **Combine with personas** - Use domain-specific personas for better results
- **Clear context** - Remove sensitive content from context when finished
- **Verify outputs** - Always verify LLM interpretations of your documentation

## 🎓 What's Next?

Now that you've mastered Confluence integration:
- Try [Jira Workflow](jira_workflow.md) for working with tickets and projects
- Explore [GitHub Code Review](github_code_review.md) to connect documentation with code
- Learn about [Document Summarization](document_summarization.md) techniques

May your knowledge base be rich and your queries insightful! ✨
