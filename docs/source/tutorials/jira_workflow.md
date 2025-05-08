# 📋 Automating Project Updates: Using Jira Integration with LLMs

CellMage's Jira integration brings your project management data directly into your notebooks, allowing you to use LLMs to analyze tickets, generate summaries, create documentation, and automate routine tasks. This tutorial will show you how to leverage this powerful integration.

## 🛠️ Setting Up Jira Integration

1. First, install CellMage with Jira support:

```bash
pip install "cellmage[jira]"
```

2. Create an Atlassian API Token:
   - Go to https://id.atlassian.com/manage-profile/security/api-tokens
   - Click "Create API token"
   - Give it a name like "CellMage Integration" and click "Create"
   - Copy your token

3. Configure your environment:

```bash
# In your terminal or .env file
export JIRA_URL=https://your-company.atlassian.net
export JIRA_USER_EMAIL=your.email@company.com
export JIRA_API_TOKEN=your_atlassian_api_token
```

## 🚀 Basic Usage

Let's start with basic ticket fetching and analysis:

```ipython
# Load the CellMage extension
%load_ext cellmage
```

### Fetching a Single Ticket

```ipython
# Fetch a specific Jira ticket and add it to chat history
%jira PROJECT-123

# Now ask the LLM about it
%%llm
Summarize this ticket. What's the main issue, who's working on it,
and what's the current status?
```

### Fetching Multiple Tickets with JQL

Jira Query Language (JQL) lets you fetch multiple tickets matching specific criteria:

```ipython
# Fetch recent tickets assigned to you
%jira --jql "assignee = currentUser() ORDER BY updated DESC" --max 5

# Now ask the LLM for a summary
%%llm
Create a summary of my current tickets. Group them by priority
and identify any blockers or dependencies between them.
```

## 💡 Advanced Usage and Options

The `%jira` magic command includes several options to customize your workflow:

```ipython
# Add a ticket as system message instead of user message
%jira PROJECT-123 --system

# Only display ticket without adding to history
%jira PROJECT-123 --show

# Get tickets from a specific sprint
%jira --jql "sprint in openSprints() AND project = PROJECT" --max 10

# Focus on high priority bugs
%jira --jql "priority in (Highest, High) AND issuetype = Bug" --max 8
```

## 🔄 Common Jira Workflow Automations

### 1. Sprint Planning Assistant

```ipython
# Fetch all tickets in the upcoming sprint
%jira --jql "sprint in futureSprints() AND project = PROJECT ORDER BY priority DESC" --max 15

%%llm
Based on these tickets, help me prepare for sprint planning:
1. Group the tickets by component or area
2. Identify any dependencies between tickets
3. Suggest a logical order for tackling these tickets
4. Highlight any tickets that may need clarification or refinement
5. Estimate relative complexity (not time) for each ticket
```

### 2. Sprint Retrospective Summary

```ipython
# Fetch all tickets completed in the last sprint
%jira --jql "project = PROJECT AND sprint in closedSprints() AND status = Done AND sprint = 'Sprint 42'" --max 20

%%llm
Create a comprehensive sprint retrospective summary based on these tickets:
1. Summarize what was accomplished this sprint
2. Group accomplishments by feature area or component
3. Identify any patterns in the work completed
4. Note any tickets that took particularly long or were completed quickly
5. Suggest areas of focus for the next sprint
```

### 3. Status Report Generator

```ipython
# Fetch your in-progress tickets
%jira --jql "assignee = currentUser() AND status in ('In Progress', 'Review') ORDER BY updated DESC" --max 10

%%llm
Create a professional status report for my manager, including:
1. Summary of what I'm currently working on
2. Progress made this week
3. Blockers or challenges I'm facing
4. What I plan to work on next
5. Any help or resources I need

Format it in a clear, concise way suitable for an email.
```

### 4. Technical Documentation Generator

```ipython
# Fetch a feature ticket with all its subtasks
%jira FEATURE-456
%jira --jql "parent = FEATURE-456" --max 15

%%llm
Based on this feature and its subtasks, generate technical documentation that includes:
1. An overview of the feature's purpose
2. System architecture and components affected
3. API changes or new endpoints created
4. Database changes
5. Testing considerations
6. Deployment notes
```

### 5. Ticket Quality Improvement

```ipython
# Fetch a specific ticket that needs improvement
%jira PROJECT-789

%%llm
This ticket seems unclear. Please suggest improvements to make it more actionable:
1. Rewrite the title to be more specific
2. Expand the description with clearer context
3. Suggest what acceptance criteria should be added
4. Recommend any labels or components that should be added
5. Identify what information is missing from this ticket
```

## 🔗 Integrating Jira with Other CellMage Features

### Combining with Personas

Using specialized personas enhances your Jira workflows:

```ipython
# Create a Product Manager persona in llm_personas/product_manager.md
"""
---
name: Product Manager
model: gpt-4o
temperature: 0.2
description: A product-focused perspective for analyzing requirements and user stories.
---
You are an experienced product manager with expertise in converting business requirements into clear, actionable user stories.

When analyzing Jira tickets:
1. Identify unclear requirements or missing information
2. Suggest ways to make tickets more specific and measurable
3. Consider user perspectives and journeys
4. Think about potential edge cases and non-functional requirements
5. Maintain focus on business value and user outcomes

Always be constructive and solution-oriented in your feedback.
"""

# Apply this persona to a Jira analysis
%llm_config --persona product_manager
%jira PROJECT-123
%%llm
Review this user story and suggest improvements to make it clearer and more actionable.
```

### Combining with GitHub/GitLab Integration

Connect code changes with Jira tickets:

```ipython
# Fetch both a Jira ticket and related GitHub PR
%jira PROJECT-123
%github username/repository --pr 456

%%llm
Analyze if this pull request properly addresses the requirements in the Jira ticket.
Identify any gaps or requirements that aren't fully implemented.
```

### Using Confluence Integration with Jira

Combine Jira and Confluence for comprehensive context:

```ipython
# Load the Confluence integration
%load_ext cellmage.integrations.confluence_magic

# Fetch a Jira ticket
%jira PROJECT-123

# Fetch related documentation
%confluence SPACE:Feature Documentation

%%llm
Compare the requirements in this Jira ticket with the current feature documentation.
Identify any discrepancies or areas where the documentation needs to be updated
to reflect the ticket requirements.
```

## 🧠 Best Practices for Jira Integration

1. **Use specific JQL queries**: Narrow down your queries to fetch only relevant tickets
2. **Combine with appropriate personas**: Use product manager personas for requirement analysis, technical personas for implementation
3. **Refresh ticket data**: Re-fetch tickets after making changes to get the most current information
4. **Add system context**: Use `--system` flag for important project constraints or guidelines
5. **Handle sensitive information**: Be mindful of confidential information in Jira tickets
6. **Structure your prompts**: Ask specific questions about tickets rather than general ones

## 🚀 Next Steps

Now that you've learned how to automate project updates using Jira integration with CellMage, explore:
- [Confluence Integration](../confluence_integration.md): Combine Jira with Confluence for knowledge management
- [Advanced Configuration](../configuration.md): Customize your CellMage environment
- [Token Usage](token_usage.md): Understand and optimize token usage for large ticket sets
