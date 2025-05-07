# 🔄 Chain of Thought: Guiding LLMs through Complex Reasoning

Welcome to the Chain of Thought tutorial! This guide will help you master techniques for guiding Large Language Models through complex, multi-step reasoning processes using CellMage.

## 🎯 What You'll Learn

In this tutorial, you'll discover:
- What Chain of Thought (CoT) reasoning is and why it matters
- How to structure prompts to elicit step-by-step thinking
- Techniques for solving complex problems by breaking them down
- When and how to use different CoT approaches
- How to combine CoT with other prompting techniques

## 🧙‍♂️ Prerequisites

Before diving in, ensure you:
- Have completed the [Basic Chat](basic_chat.md) tutorial
- Are familiar with [Advanced Prompting](advanced_prompting.md) concepts
- Have CellMage loaded in your notebook:

```python
%load_ext cellmage.integrations.ipython_magic
```

## 🧠 Understanding Chain of Thought

Chain of Thought is a prompting technique that encourages LLMs to break down complex reasoning into explicit, sequential steps. By verbalizing the intermediate reasoning steps, models often produce more accurate final answers, especially for:
- Mathematical problems
- Logical reasoning tasks
- Multi-step planning
- Complex decision making

## 📊 Step 1: Basic Chain of Thought

Let's start with a simple example:

```python
%%llm
Problem: If a shirt originally costs $25 and is on sale for 20% off,
then with an additional 15% off with a coupon, what is the final price?

Please solve this step-by-step.
```

Notice how adding "Please solve this step-by-step" encourages the model to show its work.

## 🔍 Step 2: Explicitly Structured CoT

For more control over the reasoning process, outline the steps explicitly:

```python
%%llm
Problem: A train travels at 120 km/h for 2.5 hours, then at 90 km/h for 1.5 hours. What is the average speed for the entire journey?

Solve using these steps:
1. Calculate the total distance traveled
2. Calculate the total time taken
3. Apply the formula: average speed = total distance / total time
4. Express the answer in km/h
```

## 🧩 Step 3: Self-questioning CoT

Encourage the model to ask itself relevant questions during the reasoning process:

```python
%%llm
Problem: A company needs to assign 7 employees to 3 different projects. Each project requires at least 2 employees. How many different ways can they assign employees to projects?

Use self-questioning to solve this:
1. What's the key constraint in this problem?
2. How many employees will be in each project if we distribute them minimally?
3. Are there any remaining employees after minimal distribution?
4. How do we calculate the number of ways to distribute the remaining employees?
5. What formula or approach should we use for this combinatorial problem?
6. Let's calculate the final answer step by step.
```

## 🔄 Step 4: Comparative CoT

Have the model explore multiple approaches and compare them:

```python
%%llm
Problem: Find the minimum number of coins needed to make change for $0.67 using quarters ($0.25), dimes ($0.10), nickels ($0.05), and pennies ($0.01).

Solve using two different approaches:
1. Greedy algorithm approach:
   - Start with the largest denomination and use as many as possible
   - Continue with smaller denominations
   - Count the total coins used

2. Dynamic programming approach:
   - Define the subproblems
   - Build a solution table
   - Extract the answer from the table

Compare the results and explain which approach is more efficient and why.
```

## 🎭 Step 5: Persona-Based CoT

Assign specific roles to enhance reasoning quality:

```python
%%llm --persona analytical_thinker
Problem: A software team is deciding between two architectures:
- Microservices: More scalable but complex to maintain
- Monolith: Simpler but less flexible for scaling

Think through the decision process as three different experts:
1. As a Systems Architect, analyze technical tradeoffs
2. As a DevOps Engineer, consider deployment and maintenance
3. As a Product Manager, evaluate business implications

For each perspective, show your reasoning step by step before making a final recommendation.
```

## 🛠️ Step 6: Decomposition-based CoT

Break down complex problems into manageable subproblems:

```python
%%llm
Problem: Design a database schema for an online bookstore that handles inventory, customer accounts, orders, reviews, and recommendations.

Decompose this problem:
1. First, identify all the main entities needed
2. For each entity, list required attributes
3. Determine relationships between entities
4. Consider normalization principles
5. Draw conclusions about primary and foreign keys
6. Propose the final schema design

Work through each step methodically before moving to the next.
```

## 🧪 Step 7: Experimental CoT

Use "what if" scenarios to explore alternatives and deepen understanding:

```python
%%llm
Problem: A startup has $50,000 to allocate between marketing and product development. They need to decide on the optimal allocation.

Think through this problem by exploring different scenarios:
1. First, what factors should influence this decision?
2. What if they allocate 80% to product and 20% to marketing?
3. What if they allocate 50% to product and 50% to marketing?
4. What if they allocate 20% to product and 80% to marketing?
5. What risks come with each allocation?
6. Based on this analysis, what allocation would you recommend and why?

For each scenario, think through the likely outcomes step by step.
```

## 🔧 Step 8: Recursive CoT

Handle complex problems by applying CoT recursively:

```python
%%llm
Problem: Evaluate the time and space complexity of implementing a solution to find all possible subsets of a set of n distinct integers.

Apply recursive reasoning:
1. First, define the problem clearly
2. Break it down into subproblems
   2.1. How many subsets will there be in total?
   2.2. How do we systematically generate each subset?
3. For the chosen algorithm:
   3.1. Analyze the time complexity step by step
   3.2. Analyze the space complexity step by step
4. Consider edge cases
5. Summarize the final complexity in Big O notation

Show your reasoning at each step and substep.
```

## 📝 Step 9: Verification-based CoT

Incorporate verification steps to catch errors in reasoning:

```python
%%llm
Problem: There are 5 red balls, 3 blue balls, and 2 green balls in a bag. If you draw 2 balls without replacement, what is the probability that both balls are the same color?

Solve with verification:
1. Calculate the total number of ways to draw 2 balls
2. Calculate the number of ways to draw 2 red balls
3. Calculate the number of ways to draw 2 blue balls
4. Calculate the number of ways to draw 2 green balls
5. Sum the favorable outcomes
6. Calculate the probability
7. Verify your answer:
   - Check that your probability is between 0 and 1
   - Confirm the calculation with a different approach
   - Test with a simple scenario to validate your logic
```

## 🎮 Advanced CoT Applications

### Mathematical Reasoning

```python
%%llm
Problem: Prove that the sum of the first n odd numbers equals n².

Guide your proof:
1. First, write out what the first few odd numbers are
2. Sum the first few terms and look for a pattern
3. Formulate a hypothesis based on the observed pattern
4. Prove this using mathematical induction:
   a. Verify the base case
   b. Assume it's true for some k
   c. Prove it's true for k+1
5. Conclude your proof
```

### Algorithmic Design

```python
%%llm
Design an algorithm to find the longest palindromic substring in a string.

Reasoning process:
1. First, clarify what a palindromic substring is
2. Consider naive approaches and their complexities
3. Explore potential optimizations or known algorithms
4. Select an approach and justify your choice
5. Outline the algorithm step by step
6. Analyze its time and space complexity
7. Provide pseudocode for the solution
8. Test the algorithm with example cases
```

### Ethical Decision Making

```python
%%llm
Scenario: An AI system that predicts recidivism rates shows different accuracy rates across demographic groups. Should it be deployed in the criminal justice system?

Ethical reasoning framework:
1. Identify the core ethical principles at stake
2. Analyze potential benefits of deployment
3. Analyze potential harms and their distribution
4. Consider alternative approaches
5. Evaluate relevant legal and regulatory requirements
6. Weigh competing considerations
7. Formulate a nuanced recommendation with safeguards

For each step, show your detailed reasoning process.
```

## ⚠️ Limitations and Best Practices

Even with CoT techniques, be aware:

1. **LLMs can still make reasoning errors** - Always verify critical calculations or logic
2. **Excessive decomposition can consume tokens** - Find the right balance
3. **Some problems resist decomposition** - Know when other approaches might work better
4. **Models may still take shortcuts** - Explicitly request verification steps

## 🎓 What's Next?

Now that you've mastered Chain of Thought reasoning:
- Learn about [Streaming Responses](streaming_responses.md) for handling long-running CoT outputs
- Explore [Using Snippets](using_snippets.md) to provide complex context for reasoning
- Try [Data Analysis Assistant](data_analysis_assistant.md) for applying CoT to data problems

May your reasoning be clear and your conclusions sound! ✨
