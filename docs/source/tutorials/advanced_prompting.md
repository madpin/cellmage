# 🧠 Advanced Prompting: Mastering the Art of LLM Instructions

Welcome to the Advanced Prompting tutorial! This guide will help you develop sophisticated prompting techniques to get the most out of Large Language Models with CellMage.

## 🎯 What You'll Learn

This tutorial covers:
- Advanced prompting frameworks and techniques
- Role-based prompting strategies
- Creating multi-step reasoning prompts
- Working with constraints and guardrails
- Context engineering for optimal responses

## 🪄 Prerequisites

Before diving into advanced techniques, make sure:
- You're comfortable with [basic chat interactions](basic_chat.md)
- You understand how to use the `%%llm` magic command
- You have CellMage loaded in your notebook:

```ipython
%load_ext cellmage
```

## 🧙‍♂️ Advanced Prompting Techniques

### 💼 Step 1: Role Prompting

Assign specific roles to guide the LLM's perspective and expertise:

```ipython
%%llm
You are an experienced database architect specializing in NoSQL systems.

Compare MongoDB and DynamoDB, addressing:
1. Data modeling capabilities
2. Scaling characteristics
3. Use case scenarios
4. Performance considerations
```

This technique works because it activates specific knowledge domains within the LLM.

### 🎭 Step 2: Multilayer Role Prompting

For complex scenarios, define multiple roles and relationships:

```ipython
%%llm
You will act as three different experts having a roundtable discussion:
1. A cloud infrastructure specialist
2. A cybersecurity expert
3. A DevOps engineer

Topic: Implementing zero-trust security in cloud-native applications.

Present the perspective of each expert in turn, highlighting areas of agreement and disagreement.
```

### 📝 Step 3: Structured Output Formatting

Request precise output formats for easier parsing or integration:

```ipython
%%llm
Analyze the strengths and weaknesses of React, Vue, and Angular.

Format your response as a JSON object with this structure:
{
  "frameworks": [
    {
      "name": "Framework name",
      "strengths": ["strength1", "strength2", "..."],
      "weaknesses": ["weakness1", "weakness2", "..."],
      "ideal_use_cases": ["case1", "case2", "..."]
    }
  ],
  "summary": "Overall comparison summary"
}
```

### 🧩 Step 4: Few-Shot Prompting

Provide examples of the pattern you want the LLM to follow:

```ipython
%%llm
Convert these requirements into user stories using the format: "As a [role], I want [capability] so that [benefit]."

Examples:
Requirement: The system should allow users to reset their password.
User Story: As a user, I want to reset my password so that I can regain access if I forget my credentials.

Requirement: Admins need to generate monthly usage reports.
User Story: As an administrator, I want to generate monthly usage reports so that I can track system utilization.

Now convert these:
1. The system should notify users when new comments are added
2. Users need to filter search results by date range
3. Managers should be able to assign tasks to team members
```

### 🔍 Step 5: Chain of Thought Prompting

Guide the LLM through explicit reasoning steps:

```ipython
%%llm
Problem: A company needs to optimize their delivery routes. They have 5 delivery trucks and 20 locations to deliver to. What approach would you recommend?

Think through this step by step:
1. First, identify the type of problem this represents
2. List relevant algorithms or approaches
3. Compare the pros and cons of each approach
4. Recommend a specific solution with justification
5. Suggest implementation considerations
```

### ⚙️ Step 6: Working with Constraints

Impose specific constraints to shape the response:

```ipython
%%llm
Write a Python function that finds all prime numbers up to n using the Sieve of Eratosthenes.

Constraints:
- Use only standard libraries
- Include clear comments
- Optimize for readability
- Keep the function under 20 lines
- Include example usage
```

### 🎯 Step 7: Persona Layering with System Prompts

Combine personas with custom system instructions for even more control:

```ipython
# Set a base persona
%llm_config --persona code_expert

# Add a custom system instruction as a snippet
%llm_config --sys-snippet python_code_standards.md

# Your prompt now builds on both the persona and the system snippet
%%llm
Refactor this code to follow best practices:

def process(x):
  y = x*x
  if y > 100:
    return 'big'
  else:
    return 'small'
```

### 🔄 Step 8: Iterative Refinement with Self-Criticism

Ask the LLM to critique and improve its own responses:

```ipython
%%llm
Write a function to efficiently find the longest palindromic substring in a string.

After writing the solution, critique your own code for:
1. Time complexity
2. Space complexity
3. Edge cases
4. Readability

Then, provide an improved version based on your critique.
```

### 🧠 Step 9: Context Engineering

Manage context strategically to overcome token limitations:

```ipython
# First, set up relevant context
%llm_config --snippet data_schema.py --snippet requirements.md

# Ask a focused question that leverages the context
%%llm
Based on the database schema and requirements I've shared:
1. Identify potential performance bottlenecks
2. Suggest indexing strategies
3. Recommend query optimizations
```

### 🌐 Step 10: Cross-Domain Reasoning

Prompt the LLM to apply knowledge from one domain to another:

```ipython
%%llm
Explain how principles from evolutionary biology could be applied to improve machine learning algorithms.

Structure your response to:
1. Identify 3-5 key evolutionary principles
2. For each principle, explain its biological basis
3. Draw a clear parallel to a machine learning concept
4. Suggest a concrete implementation approach
```

## 🧪 Advanced Prompt Templates

Here are some powerful template structures you can adapt:

### Decision Matrix Template

```ipython
%%llm
Create a decision matrix comparing these options: [OPTIONS]

Evaluation criteria:
- [CRITERION 1]
- [CRITERION 2]
- [CRITERION 3]

For each option and criterion:
1. Provide a score from 1-5
2. Give a brief justification
3. Highlight key advantages/disadvantages

End with a recommendation based on the highest weighted score.
```

### Systematic Problem-Solving Template

```ipython
%%llm
Problem: [DESCRIBE PROBLEM]

Solve using this framework:
1. Problem definition: Restate the problem and identify key constraints
2. Root cause analysis: Identify potential underlying causes
3. Solution generation: List 3-5 possible approaches
4. Evaluation criteria: Define how you'll assess solutions
5. Analysis: Evaluate each solution against the criteria
6. Recommendation: Choose the best approach with justification
7. Implementation plan: Outline key steps to implement the solution
8. Risks and mitigations: Identify potential issues and countermeasures
```

## ⚠️ Advanced Prompting Pitfalls

Even with sophisticated prompting:

1. **Hallucinations can still occur** - Verify factual information
2. **Token limits are a constraint** - Break complex tasks into subtasks
3. **Consistency isn't guaranteed** - Use structured formats for predictability
4. **Model limitations persist** - Know when to switch to human expertise

## 🎓 What's Next?

Now that you've mastered advanced prompting techniques:
- Dive into [Chain of Thought](chain_of_thought.md) for complex reasoning
- Learn about [Working with Personas](working_with_personas.md) for specialized knowledge domains
- Explore [Conversation Management](conversation_management.md) for organizing complex dialogues

May your prompts be effective and your responses enlightening! ✨
