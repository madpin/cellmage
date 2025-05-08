# 💻 Code Generation Workflow: Building Software with LLM Assistance

Welcome to the Code Generation Workflow tutorial! This guide will help you establish an effective process for using CellMage to generate, refine, and maintain high-quality code for your projects.

## 🎯 What You'll Learn

In this tutorial, you'll discover:
- How to structure effective code generation prompts
- Techniques for iteratively refining generated code
- Strategies for testing and evaluating LLM-generated code
- Best practices for maintaining quality and readability
- Advanced workflows for complex software development

## 🧙‍♂️ Prerequisites

Before diving in, make sure:
- You have basic programming knowledge
- You understand the fundamentals of the language/framework you're using
- You have CellMage loaded in your notebook:

```ipython
%load_ext cellmage
```

## 🔍 Step 1: Understanding the Code Generation Mindset

When using LLMs for code generation, shift your thinking from "writing code" to "collaborating with an AI pair programmer":

```ipython
%%llm
I want to establish a good workflow for code generation with LLMs.
What principles should I follow to get the best results when asking you to generate code?
What are common pitfalls to avoid?
```

## 📝 Step 2: Defining Clear Requirements

The quality of your prompt determines the quality of generated code. Start by clearly defining requirements:

```ipython
%%llm
I need to build a Python function that:
1. Takes a list of URLs as input
2. Fetches the content from each URL (HTML)
3. Extracts all image URLs from the HTML
4. Downloads the images to a specified directory
5. Returns a dictionary mapping original URLs to lists of downloaded image paths

Requirements:
- Handle connection errors gracefully
- Support timeout configuration
- Include progress reporting
- Use async/await for efficient fetching
```

## 🧩 Step 3: Breaking Down Complex Tasks

For complex code generation, break tasks into manageable components:

```ipython
%%llm
I want to build a web scraper for product information. Let's break this down:

First, design the overall architecture with these components:
1. URL collector module
2. HTML fetcher module
3. Content parser module
4. Data storage module
5. Rate limiter and retry logic
6. Main orchestrator

For each component, outline:
- Key functions/classes
- Input/output interfaces
- Dependencies
- Error handling approach
```

## 🔄 Step 4: Iterative Refinement

Generated code often needs refinement. Use a multi-step approach:

```ipython
# First draft
%%llm
Write a Python class for a simple in-memory key-value store with expiration.
Include methods for get, set, delete, and expire_old_keys.

# Refinement based on issues you identify
%%llm
The code you provided looks good, but I'd like to make these improvements:
1. Add type hints to all methods
2. Implement a thread-safe version using locks
3. Add an option to persist the cache to disk
4. Include unit tests for the core functionality

Can you update the implementation with these changes?
```

## 🧪 Step 5: Testing Generated Code

Always ask for tests alongside implementations:

```ipython
%%llm
Write a function to validate JSON against a schema, and include comprehensive unit tests.
The function should:
- Take a JSON string or dictionary and a schema object
- Validate the JSON against the schema
- Return a tuple (is_valid, errors_list)
- Handle common edge cases

Include pytest test cases that cover:
- Valid JSON validation
- Invalid JSON structure
- Missing required fields
- Type mismatches
- Nested schema validation
```

## 📚 Step 6: Documentation and Comments

Request well-documented code to enhance maintainability:

```ipython
%%llm
Write a Python utility module for secure password handling with the following functions:
1. hash_password(password: str) -> str
2. verify_password(password: str, hashed: str) -> bool
3. generate_password(length: int, complexity: str) -> str

For each function:
- Include detailed docstrings in Google format
- Add explanatory comments for complex operations
- Provide typing information
- Include usage examples

Also add module-level documentation explaining security considerations.
```

## 🛠️ Step 7: Algorithm Design and Optimization

When performance matters, provide specific requirements:

```ipython
%%llm
I need an efficient algorithm for finding all pairs of numbers in an array that sum to a given target.

Requirements:
- Time complexity should be better than O(n²)
- Space complexity should be discussed and optimized
- The solution should handle duplicates correctly
- Include analysis of edge cases and constraints

Please provide:
1. The algorithm explanation
2. Step-by-step derivation of your approach
3. Python implementation with comments
4. Time and space complexity analysis
5. Test cases including edge cases
```

## 🔀 Step 8: Exploring Alternative Approaches

Generate multiple solutions to select the best approach:

```ipython
%%llm
I need to implement a rate limiter for an API. Generate three different approaches:
1. A simple time-window counter implementation
2. A token bucket algorithm implementation
3. A leaky bucket algorithm implementation

For each approach:
- Explain how it works
- Provide a Python implementation
- List pros and cons
- Identify ideal use cases

Then recommend which approach best fits a high-traffic microservice with bursty workloads.
```

## 📄 Step 9: Working with Existing Codebases

Guide the LLM on how to integrate with your existing code:

```ipython
# First, provide context about your existing code
%llm_config --snippet database_manager.py
%llm_config --snippet config.py

%%llm
I need to extend our database_manager.py module with a new feature for caching query results.
The cache should:
1. Use Redis as the backend (already configured in config.py)
2. Cache query results based on a hash of the query and parameters
3. Support TTL configuration per query type
4. Include cache invalidation when related data changes
5. Follow our existing coding style and patterns

Please generate the implementation that integrates with our existing code.
```

## 🛡️ Step 10: Code Review and Security

Use CellMage to review code for security issues:

```ipython
%llm_config --snippet user_authentication.py

%%llm
Please review the user_authentication.py file for security vulnerabilities, focusing on:
1. Proper password storage and comparison
2. SQL injection vulnerabilities
3. Session management security
4. CSRF protection
5. XSS vulnerabilities
6. Proper use of encryption

For each issue found, explain:
- The security risk
- How it could be exploited
- A recommended fix with code examples
```

## 🧪 Advanced Code Generation Techniques

### Implementing Design Patterns

```ipython
%%llm
Implement the Observer design pattern for a weather monitoring system in Python.

The system should:
1. Have a WeatherData subject that maintains state (temperature, humidity, pressure)
2. Support multiple display elements that observe the weather data
3. Update displays automatically when weather data changes
4. Allow for easy addition of new types of displays

Include:
- Abstract classes/interfaces for observers and subjects
- Concrete implementations of the WeatherData subject
- At least three different display observers
- A demo showing the system in action
```

### API Client Generation

```ipython
%%llm
Generate a Python client for interacting with the following REST API endpoints:

API Base URL: https://api.example.com/v1
Authentication: Bearer token in header
Endpoints:
- GET /users - List users (params: page, limit, role)
- GET /users/{id} - Get user details
- POST /users - Create user (fields: name, email, role)
- PUT /users/{id} - Update user
- DELETE /users/{id} - Delete user

Create a well-structured client that:
1. Handles authentication automatically
2. Provides intuitive methods for each endpoint
3. Processes errors consistently
4. Includes retry logic for failed requests
5. Supports both sync and async usage
6. Has comprehensive docstrings for each method
```

### Full-Stack Feature Implementation

```ipython
%%llm
I'm building a task management application and need to implement a "task assignment" feature.

Technology stack:
- Backend: FastAPI + SQLAlchemy + PostgreSQL
- Frontend: React + TypeScript
- Authentication: OAuth2 with JWT

Requirements:
1. Users should be able to assign tasks to other team members
2. Assigned users should receive notifications
3. Track assignment history for audit purposes
4. Support bulk assignments

Please create:
1. Database schema changes (SQLAlchemy models)
2. Backend API endpoints (FastAPI routes)
3. Frontend components for task assignment
4. Integration strategy between frontend and backend
```

## ⚠️ Limitations and Best Practices

When working with generated code:

1. **Never deploy without review** - Always verify generated code for logic errors
2. **Test rigorously** - Generated code may contain subtle bugs
3. **Verify security implications** - LLMs might not follow security best practices by default
4. **Understand before using** - Don't use code you don't understand
5. **Maintain consistency** - Ensure generated code follows your project's style and patterns

## 🚦 Code Generation Best Practices

- **Provide clear context** - Include information about your environment, constraints, and style
- **Start small, iterate** - Begin with core functionality and refine gradually
- **Request explanations** - Ask the LLM to explain complex parts of generated code
- **Be explicit about quality** - Specify coding standards, error handling requirements, etc.
- **Validate edge cases** - Explicitly test generated code with edge cases
- **Maintain human oversight** - Use LLMs as tools, not replacements for software engineering judgment

## 🎓 What's Next?

Now that you've mastered the code generation workflow:
- Try [GitHub Code Review](github_code_review.md) to integrate with your version control workflow
- Explore [Document Summarization](document_summarization.md) to generate documentation from code
- Learn about [Advanced Prompting](advanced_prompting.md) to refine your code generation skills

May your code be elegant and your bugs be few! ✨
