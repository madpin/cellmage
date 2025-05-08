# 📑 Document Summarization: Extracting Insights from Text

Welcome to the Document Summarization tutorial! This guide will help you use CellMage to efficiently extract key information from documents, generate concise summaries, and transform unstructured text into structured knowledge.

## 🎯 What You'll Learn

In this tutorial, you'll discover:
- How to process and summarize various document types
- Techniques for extracting specific information from lengthy texts
- Strategies for generating different types of summaries
- Methods for converting documents into structured formats
- Advanced workflows for document analysis tasks

## 🧙‍♂️ Prerequisites

Before diving in, make sure:
- You have basic knowledge of Python
- You have CellMage loaded in your notebook:
  ```ipython
  %load_ext cellmage
  ```
- You have document handling libraries installed:
  ```bash
  pip install PyPDF2 docx pandas
  ```

## 📝 Step 1: Loading Document Content

First, let's explore how to load content from different file types:

```ipython
# For PDF files
from PyPDF2 import PdfReader

def extract_text_from_pdf(file_path):
    """Extract text content from a PDF file."""
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

# For Word documents
from docx import Document

def extract_text_from_docx(file_path):
    """Extract text content from a Word document."""
    doc = Document(file_path)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

# For text files
def extract_text_from_txt(file_path):
    """Extract text content from a text file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

# Example usage
pdf_text = extract_text_from_pdf('example.pdf')
```

## 🔍 Step 2: Basic Document Summarization

Now that you have extracted text, use CellMage to generate a summary:

```ipython
# Load the document content into CellMage context
%llm_config --snippet pdf_text[:2000]  # First 2000 chars as context

# Request a summary
%%llm
Please provide a concise summary of this document that captures:
1. The main topic and purpose
2. Key points or arguments
3. Important conclusions or recommendations
4. Overall structure of the document

Keep the summary to 3-4 paragraphs maximum.
```

## 📊 Step 3: Extracting Structured Information

Extract specific information from documents into structured formats:

```ipython
# First provide the document context
%llm_config --snippet pdf_text

%%llm
From this document, extract the following information into a structured format:
1. All mentioned people and their roles/affiliations
2. Key statistics and numerical data
3. Dates and timeline information
4. Organizations/companies mentioned
5. Technical terms with their definitions (if available)

Format the output as a structured JSON with these categories as keys.
```

## 📋 Step 4: Creating Executive Summaries

Generate concise executive summaries for busy stakeholders:

```ipython
%llm_config --snippet pdf_text

%%llm
Create a one-page executive summary of this document that:
1. Opens with a single-sentence overview
2. Highlights 3-5 key takeaways
3. Summarizes business implications
4. Includes recommended next steps
5. Uses bullet points where appropriate for scannability

The summary should be suitable for executives who have no time to read the full document.
```

## 🧠 Step 5: Topic Extraction and Classification

Identify the main topics covered in a document:

```ipython
%llm_config --snippet pdf_text

%%llm
Analyze this document and:
1. Identify the main topics/themes covered
2. For each topic, provide a brief description and key related points
3. Estimate what percentage of the document is devoted to each topic
4. Classify the overall document type (e.g., research paper, technical report, policy document)

Present the information in a structured format suitable for understanding document composition.
```

## 🔄 Step 6: Comparative Document Analysis

Compare multiple documents on the same subject:

```ipython
# Load multiple documents
%llm_config --snippet document1_text[:1500]
%llm_config --snippet document2_text[:1500]
%llm_config --snippet document3_text[:1500]

%%llm
Compare these three documents on the same topic and create a report that:
1. Identifies common themes and points of agreement
2. Highlights key differences in approach or perspective
3. Summarizes unique contributions from each document
4. Creates a comprehensive view that synthesizes the information
5. Notes any contradictions or inconsistencies between sources

Structure this as a comparative analysis report.
```

## 📝 Step 7: Question Answering from Documents

Extract specific answers from lengthy documents:

```ipython
%llm_config --snippet technical_document

%%llm
Based on the technical document provided, please answer these questions:
1. What is the maximum throughput capacity described in the document?
2. What are the listed system requirements?
3. What security protocols are mentioned?
4. What are the known limitations discussed in section 5?
5. How does the proposed solution compare to existing alternatives?

Provide direct answers with page/section references where possible.
```

## 🧪 Step 8: Document Transformation

Convert documents into different formats for various purposes:

```ipython
%llm_config --snippet research_paper

%%llm
Transform this research paper into:
1. A blog post explaining the findings to a general audience
2. A concise set of bullet points for a presentation slide
3. A series of tweets (5-7) highlighting key discoveries
4. An abstract for a non-technical audience

Each transformation should maintain accuracy while adapting the tone and complexity for its intended purpose.
```

## 📊 Step 9: Creating Document Metadata

Generate useful metadata for document management:

```ipython
%llm_config --snippet document_text

%%llm
Generate comprehensive metadata for this document including:
1. A suggested title (if not already clear)
2. 5-7 relevant keywords or tags
3. Primary category and subcategories
4. Target audience
5. Complexity level (beginner/intermediate/advanced)
6. Estimated reading time
7. A short description (2-3 sentences)

Format as a metadata dictionary suitable for a document management system.
```

## 🧠 Step 10: Insight Extraction and Analysis

Go beyond summarization to extract deeper insights:

```ipython
%llm_config --snippet market_research_report

%%llm
Analyze this market research report and provide:
1. Key market trends identified and their implications
2. SWOT analysis of the main product/company discussed
3. Competitive landscape overview
4. Strategic recommendations based on the data
5. Potential future scenarios suggested by the findings
6. Critical data points that support these insights

Structure this as a strategic insights brief for management decision-making.
```

## 🧪 Advanced Document Processing Techniques

### Processing Large Documents

For documents that exceed context limits:

```ipython
# Split document into chunks
def chunk_document(text, chunk_size=4000, overlap=200):
    """Split document into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        # Try to find a paragraph break for cleaner chunking
        if end < len(text) and end - start > overlap:
            # Look for paragraph break near the end of chunk
            paragraph_break = text.rfind('\n\n', start + chunk_size - overlap, end)
            if paragraph_break != -1:
                end = paragraph_break
        chunks.append(text[start:end])
        start = end - overlap if end < len(text) else end
    return chunks

# Process each chunk
document_chunks = chunk_document(long_document_text)
summaries = []

for i, chunk in enumerate(document_chunks):
    %llm_config --snippet chunk

    chunk_prompt = f"""
    This is chunk {i+1} of {len(document_chunks)} from a larger document.

    Please provide a summary of this section that includes:
    1. Main topics covered
    2. Key points and findings
    3. Any conclusions or recommendations

    Keep the summary concise (200-300 words).
    """

    # Execute this in a notebook cell for each chunk
    # %%llm
    # chunk_prompt
    # Then collect the response into summaries list

# Finally, synthesize the chunk summaries
%llm_config --snippet "\n\n".join(summaries)

%%llm
You've been provided with summaries of different sections from a single document.
Please synthesize these into a coherent overall summary that:
1. Maintains the document's narrative flow
2. Preserves the key points from each section
3. Eliminates redundancies between sections
4. Creates a unified document summary of approximately 1000 words
```

### Multi-Document Synthesis

For analyzing collections of related documents:

```ipython
# Assume you have summaries of multiple related documents
document_summaries = {
    "policy_doc1.pdf": policy1_summary,
    "policy_doc2.pdf": policy2_summary,
    "policy_doc3.pdf": policy3_summary,
    "implementation_guide.pdf": implementation_summary,
    "technical_specs.pdf": specs_summary
}

# Load all summaries
for doc_name, summary in document_summaries.items():
    %llm_config --snippet f"Document: {doc_name}\nSummary:\n{summary[:1000]}"

%%llm
You've been provided with summaries of multiple related documents about the same policy/system.
Create a comprehensive knowledge synthesis that:

1. Provides an integrated understanding of the entire system/policy
2. Identifies how the documents relate to and complement each other
3. Resolves any contradictions or inconsistencies between documents
4. Creates a unified "source of truth" from these separate documents
5. Notes any gaps in information that might require additional documentation

Structure this as a knowledge base article that serves as an authoritative reference.
```

### Extracting Action Items

```ipython
%llm_config --snippet meeting_transcript

%%llm
Review this meeting transcript and:
1. Identify all action items and commitments made
2. Extract who is responsible for each item
3. Note any mentioned deadlines or timelines
4. Categorize actions by priority if indicated
5. Flag any dependencies between action items

Format this as an action item tracker suitable for project management follow-up.
```

## ⚠️ Limitations and Best Practices

When working with document summarization:

1. **Context limitations** - Be aware of token limits; break long documents into chunks
2. **Verification required** - Always verify extracted information against the source
3. **Detail loss** - Summarization inherently loses nuance; critical details may be omitted
4. **Domain knowledge** - LLMs may miss domain-specific significance without guidance
5. **Source integrity** - The quality of outputs depends on input document quality

## 🚦 Document Processing Best Practices

- **Specify purpose** - Clearly define your summarization goal (overview, details, action items, etc.)
- **Provide guidance** - Tell the LLM what to focus on and what to ignore
- **Use structured outputs** - Request specific formats for easier processing
- **Iterate refinements** - Start with general summaries, then request specific details
- **Combine approaches** - Use both chunk-by-chunk and holistic analysis for comprehensive understanding

## 🎓 What's Next?

Now that you've learned to summarize and process documents:
- Explore [Working with Personas](working_with_personas.md) to tailor summaries for specific audiences
- Try [Jira Workflow](jira_workflow.md) to integrate documents into task management
- Learn about [Chain of Thought](chain_of_thought.md) for deeper document analysis

May your documents reveal their secrets through magical distillation! ✨
