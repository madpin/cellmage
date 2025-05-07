# 📊 Data Analysis Assistant: LLM-Powered Data Exploration

Welcome to the Data Analysis Assistant tutorial! This guide will help you leverage CellMage's capabilities to enhance your data analysis workflows, generate insights, and create visualizations through natural language interactions.

## 🎯 What You'll Learn

In this tutorial, you'll discover:
- How to use CellMage as an intelligent data analysis companion
- Techniques for data exploration and visualization through natural language
- Strategies for generating and refining analysis code
- Methods for explaining complex statistical concepts
- Best practices for data-centric LLM workflows

## 🧙‍♂️ Prerequisites

Before diving in, make sure:
- You have basic knowledge of Python data science libraries (pandas, matplotlib, etc.)
- You have a Jupyter notebook environment set up
- You have CellMage installed and loaded:
  ```ipython
  %load_ext cellmage.integrations.ipython_magic
  ```
- You have common data science packages installed:
  ```bash
  pip install pandas matplotlib seaborn scikit-learn
  ```

## 📝 Step 1: Preparing Your Data Analysis Environment

Let's start by setting up an environment with some sample data:

```ipython
# Import necessary libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Set plot styling
plt.style.use('ggplot')
%matplotlib inline

# Load sample dataset
df = pd.read_csv('https://raw.githubusercontent.com/mwaskom/seaborn-data/master/tips.csv')

# Display the first few rows
df.head()
```

## 🧬 Step 2: Basic Data Exploration with LLM

Use CellMage to explore your dataset through natural language:

```ipython
# Add your dataframe to the context
%llm_config --snippet df.head().to_string()
%llm_config --snippet df.describe().to_string()
%llm_config --snippet df.info()

# Ask questions about your data
%%llm
I'm working with a dataset called 'df'. Based on what you can see:
1. What kind of data is this?
2. What are the main variables?
3. What initial insights can you provide?
4. What analysis would you recommend?
```

## 📈 Step 3: Generating Data Visualization Code

Ask CellMage to help you create visualizations:

```ipython
%%llm
Generate Python code to create these visualizations for my tips dataset:
1. A histogram of tip amounts
2. A scatter plot of bill amount vs. tip amount, colored by time of day
3. A box plot showing tip percentage across different days of the week
4. A heatmap of correlations between numerical variables

Make sure the code is well-commented and uses seaborn for better aesthetics.
```

Now execute the generated code in a new cell to see your visualizations.

## 🔍 Step 4: Targeted Data Analysis

Ask for specific analyses based on your preliminary findings:

```ipython
%%llm
Based on the tips dataset, generate code to analyze:
1. Whether there's a statistically significant difference in tip percentages between lunch and dinner
2. If the day of the week affects tipping behavior
3. The relationship between party size and average tip percentage

Include proper statistical tests and clear explanations of the results.
```

## 🧠 Step 5: Statistical Concept Explanations

When you encounter unfamiliar statistical concepts:

```ipython
%%llm
Please explain the following concepts in the context of our tips dataset analysis:
1. What is a t-test and when should I use it?
2. What does p-value mean in our analysis?
3. What are the assumptions of linear regression?
4. How should I interpret the correlation coefficient?

Explain with simple examples using our restaurant tipping context.
```

## 🛠️ Step 6: Data Cleaning and Preparation

Get help with data cleaning and transformation:

```ipython
%%llm
Generate code to clean and prepare the tips dataset:
1. Create a new 'tip_percentage' column (tip as a percentage of total bill)
2. Convert categorical variables to appropriate formats for modeling
3. Check for and handle any potential outliers
4. Split the data into training and testing sets for a model that predicts tip percentage

Include explanations for each preprocessing step.
```

## 🤖 Step 7: Model Building Assistance

Ask for help creating predictive models:

```ipython
%%llm
Write code to build three different models to predict tip percentage:
1. A simple linear regression model
2. A random forest regressor
3. A gradient boosting model

Include feature selection, model training, evaluation metrics, and a comparison of the models' performance.
```

## 📊 Step 8: Results Interpretation

After running analyses, ask the LLM to help interpret results:

```ipython
# First, run your analysis code and capture the output
# Then paste relevant results as context

%llm_config --snippet """
Model Results:
Linear Regression R² = 0.45
Random Forest R² = 0.67
Gradient Boosting R² = 0.72

Feature Importances:
- party_size: 0.35
- total_bill: 0.25
- day (Saturday): 0.15
- time (Dinner): 0.12
- smoker (Yes): 0.08
- day (Sunday): 0.05
"""

%%llm
Interpret these model results for predicting tip percentage:
1. Which model performed best and why?
2. What are the most important factors influencing tip amounts?
3. How would you explain these results to a restaurant manager?
4. What recommendations would you make based on this analysis?
```

## 📝 Step 9: Generating Analysis Reports

Use CellMage to help create professional reports:

```ipython
%%llm
Based on our analysis of the restaurant tipping dataset, generate a structured report with these sections:
1. Executive Summary (2-3 paragraphs)
2. Methodology (brief description of data and approaches)
3. Key Findings (bullet points of 4-5 main discoveries)
4. Visualizations to Include (list the most important ones)
5. Business Recommendations (3-4 actionable insights)
6. Future Analysis Suggestions

Write this for a restaurant management audience.
```

## 🔄 Step 10: Refining Analysis Iteratively

Use the iterative nature of CellMage to refine your analysis:

```ipython
%%llm
The scatter plot showing tip amount vs total bill revealed a potential non-linear relationship.
Suggest three different transformations we could apply, and generate code to:
1. Apply these transformations
2. Visualize the transformed relationships
3. Determine which transformation makes the relationship most linear
4. Rebuild our regression model with the best transformation
```

## 🧪 Advanced Data Analysis Applications

### Time Series Analysis

```ipython
# First load a time series dataset
ts_data = pd.read_csv('https://raw.githubusercontent.com/jbrownlee/Datasets/master/airline-passengers.csv')
ts_data['Month'] = pd.to_datetime(ts_data['Month'])
ts_data.set_index('Month', inplace=True)
ts_data.head()

%%llm
Generate comprehensive time series analysis code for this airline passenger dataset:
1. Decompose the series into trend, seasonal, and residual components
2. Test for stationarity and apply transformations if needed
3. Build and evaluate a forecasting model (ARIMA or Prophet)
4. Generate and visualize a 12-month forecast with confidence intervals
5. Explain key insights about seasonality and trends

Include well-commented code and explanations.
```

### Exploratory Data Analysis (EDA) Pipeline

```ipython
%%llm
Create a reusable EDA function that I can apply to any dataset. The function should:
1. Provide basic statistics (missing values, duplicates, descriptive stats)
2. Generate appropriate visualizations based on data types
3. Identify potential outliers and unusual patterns
4. Examine correlations and relationships between variables
5. Suggest potential feature engineering steps
6. Output a summary of findings

Make it modular and well-commented so I can adapt it for future datasets.
```

### Interactive Dashboard Code Generator

```ipython
%%llm
Generate code for a simple Plotly Dash application that creates an interactive dashboard for the tips dataset with:
1. A dropdown to select variables for the x and y axes
2. Filter options for categorical variables (day, time, smoker)
3. Radio buttons to switch between different chart types
4. A statistics panel showing key metrics about the selected data
5. A data table showing the filtered records

Include all necessary code to run the application locally.
```

## ⚠️ Limitations and Best Practices

Working with data and LLMs has some important considerations:

1. **Data privacy** - Be careful not to share sensitive data with LLMs
2. **Verification is essential** - Always review and validate generated code and conclusions
3. **Context limitations** - Large datasets may exceed token limits; share summaries instead
4. **Statistical accuracy** - Double-check statistical claims and methodologies
5. **Code execution** - Test generated code on small data subsets before running on large datasets

## 🚦 Data Analysis Best Practices

- **Start broad, then narrow** - Begin with exploratory questions before diving into specifics
- **Provide clear context** - Share data types, sizes, and descriptive statistics
- **Ask for explanations** - Request comments in generated code to improve understanding
- **Iterate on results** - Use outputs to inform your next set of questions
- **Combine expertise** - Use LLM suggestions alongside your domain knowledge

## 🎓 What's Next?

Now that you've learned to use CellMage for data analysis:
- Explore [Code Generation Workflow](code_generation_workflow.md) for more complex data projects
- Try [Document Summarization](document_summarization.md) for analyzing text data
- Learn about [Chain of Thought](chain_of_thought.md) techniques for complex analytical reasoning

May your data reveal its secrets through magical assistance! ✨
