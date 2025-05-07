# 🧪 Code Review with CellMage: Integrating with GitHub/GitLab

CellMage's integration with GitHub and GitLab allows you to bring repositories and pull/merge requests directly into your notebooks for powerful AI-assisted code reviews and analysis. This tutorial will show you how to use these integrations effectively.

## 🛠️ Setting Up the Integrations

### GitHub Integration Setup

1. First, install CellMage with GitHub support:

```bash
pip install "cellmage[github]"
```

2. Create a GitHub Personal Access Token:
   - Go to GitHub → Settings → Developer settings → Personal access tokens
   - Generate a new token with at least `repo` scope (for private repositories) or `public_repo` (for public repos)
   - Copy your token

3. Configure your environment:

```bash
# In your terminal or .env file
export GITHUB_TOKEN=your_personal_access_token
```

### GitLab Integration Setup

1. First, install CellMage with GitLab support:

```bash
pip install "cellmage[gitlab]"
```

2. Create a GitLab Personal Access Token:
   - Go to GitLab → Preferences → Access Tokens
   - Create a token with `api` scope for full access or `read_api` for read-only access
   - Copy your token

3. Configure your environment:

```bash
# In your terminal or .env file
export GITLAB_URL=https://gitlab.com  # Or your self-hosted GitLab URL
export GITLAB_PAT=your_gitlab_personal_access_token
```

## 🚀 Basic Usage

Let's start with basic repository analysis:

```python
# Load the CellMage extension
%load_ext cellmage.integrations.ipython_magic

# For GitHub repositories
%load_ext cellmage.integrations.github_magic

# For GitLab repositories
%load_ext cellmage.integrations.gitlab_magic
```

### Fetching a GitHub Repository

```python
# Fetch a GitHub repository and add it to chat history
%github username/repository

# Now ask the LLM about it
%%llm
Based on the GitHub repository I just provided, can you describe its architecture
and main components? What patterns does it use?
```

### Fetching a GitLab Repository

```python
# Fetch a GitLab repository and add it to chat history
%gitlab namespace/project

# Now ask the LLM about it
%%llm
Can you analyze this GitLab project's structure and explain its key modules?
```

## 🔍 Code Review Workflows

### GitHub Pull Request Review

Pull requests contain valuable context about code changes. Let's review one:

```python
# Fetch a specific pull request
%github username/repository --pr 123

# Ask for a code review
%%llm --persona code_reviewer
Please review this pull request, focusing on:
1. Potential bugs or edge cases
2. Performance considerations
3. Adherence to best practices
4. Security concerns
5. Test coverage
```

### GitLab Merge Request Review

Similarly, for GitLab merge requests:

```python
# Fetch a specific merge request
%gitlab namespace/project --mr 456

# Ask for a code review
%%llm --persona code_reviewer
Please perform a comprehensive review of this merge request. Identify any issues,
suggest improvements, and highlight what's been done well.
```

## 🎛️ Advanced Options

Both GitHub and GitLab integrations provide options to customize the content fetched:

### GitHub Advanced Options

```python
# Clean mode (focuses on code by excluding non-essential files)
%github username/repository --clean

# Add as system message instead of user message
%github username/repository --system

# Only display content without adding to history
%github username/repository --show

# Include full code content (may be very large)
%github username/repository --full-code

# Exclude specific directories, files, or extensions
%github username/repository --exclude-dir node_modules --exclude-ext .json
```

### GitLab Advanced Options

```python
# Clean mode
%gitlab namespace/project --clean

# Add as system message
%gitlab namespace/project --system

# Only display content without adding to history
%gitlab namespace/project --show
```

## 📋 Real-World Code Review Scenarios

Let's look at some real-world scenarios where CellMage + GitHub/GitLab integration shines:

### 1. Code Architecture Assessment

```python
# Fetch repository
%github username/complex-project

%%llm --persona architecture_expert
Based on this repository:
1. Create a high-level architecture diagram (describe it in text)
2. Identify the main design patterns in use
3. Suggest improvements to the overall architecture
4. Highlight any potential scalability concerns
```

### 2. Security Audit

```python
# Fetch repository with focus on code
%github username/webapp --clean

%%llm --persona security_expert
Perform a security audit of this codebase:
1. Identify potential security vulnerabilities
2. Check for common OWASP issues like SQL injection, XSS, etc.
3. Analyze authentication and authorization mechanisms
4. Suggest security improvements
```

### 3. Performance Review

```python
# Fetch a performance-related pull request
%github username/performance-project --pr 42

%%llm --model gpt-4o
This PR aims to improve performance. Please:
1. Analyze the approach taken
2. Identify any potential performance bottlenecks that remain
3. Suggest alternative optimization strategies
4. Explain the trade-offs between readability and performance in this PR
```

### 4. Onboarding to New Codebase

```python
# Fetch repository
%gitlab namespace/new-project

%%llm
I'm a new developer joining this project. Could you:
1. Explain how the codebase is structured
2. Identify the key entry points and core functionality
3. Outline the main dependencies and how they're used
4. Suggest where to start if I need to add a new feature
```

## 💡 Best Practices for AI-Assisted Code Review

When using CellMage with GitHub/GitLab for code reviews:

1. **Use the right persona**: Different codebases benefit from different reviewer personas
2. **Be specific in your prompts**: Ask about specific aspects you want reviewed
3. **Handle large repositories carefully**: Use `--clean` and exclusion options for big repos
4. **Combine with snippets**: Add project documentation as snippets for better context
5. **Break down complex reviews**: Review one component or issue at a time
6. **Verify AI suggestions**: Always validate recommendations before implementing

## 🧠 Creating a Custom Code Reviewer Persona

To optimize your code review workflow, create a specialized code reviewer persona:

```markdown
---
name: Technical Code Reviewer
model: gpt-4o
temperature: 0.1
description: A detail-oriented code reviewer focused on technical quality and best practices
---
You are an experienced senior software engineer conducting a detailed code review.

Focus on these aspects in code review:
1. Correctness: Identify logical errors, edge cases, and potential bugs
2. Performance: Highlight inefficient algorithms, unnecessary computations, and optimization opportunities
3. Maintainability: Assess code organization, naming conventions, and documentation
4. Security: Point out potential vulnerabilities or security anti-patterns
5. Testing: Evaluate test coverage and suggest additional test cases

When reviewing:
- Format your review as a structured list of findings
- Rate issues by severity (Critical/Major/Minor)
- Always explain WHY something is problematic, not just WHAT is wrong
- Where appropriate, suggest specific code improvements
- Acknowledge good practices and well-written code
- Consider language-specific idioms and best practices
```

## 🚀 Next Steps

Now that you've learned how to use CellMage for code review with GitHub and GitLab, explore:
- [Automating Project Updates with Jira](jira_workflow.md): Integrate Jira tickets with your review workflow
- [Advanced Prompting](advanced_prompting.md): Learn sophisticated prompting techniques for better reviews
- [Understanding Token Usage](token_usage.md): Optimize token usage for large codebases
