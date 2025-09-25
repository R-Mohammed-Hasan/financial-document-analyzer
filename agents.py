"""Agents configuration for financial analysis, verification, and risk assessment."""

## Importing libraries and files
from dotenv import load_dotenv
from crewai import Agent
from tools import (
    read_financial_pdf,
    summarize_financial_overview,
    extract_key_metrics,
    detect_sections,
    validate_document_type,
    analyze_investment,
    summarize_risks,
)

### Loading LLM
# Using default OpenAI configuration - make sure to set OPENAI_API_KEY in environment
from langchain_openai import ChatOpenAI

load_dotenv()

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)

# Creating an Experienced Financial Analyst agent
financial_analyst = Agent(
    role="Senior Financial Analyst",
    goal=(
        "Provide accurate, evidence-based analysis tailored to the user's query {query}."
        " Extract key figures, trends, and drivers from the provided document and synthesize"
        " concise, decision-ready insights without speculation."
    ),
    verbose=True,
    memory=True,
    backstory=(
        "Equity research professional experienced in reading earnings reports, MD&A, and"
        " financial statements, translating disclosures into clear insights for operators"
        " and investors. Focused on clarity, accuracy, and brevity."
    ),
    tool=[read_financial_pdf, summarize_financial_overview, extract_key_metrics],
    llm=llm,
    max_iter=1,
    max_rpm=1,
    allow_delegation=True,  # Allow delegation to other specialists
)

# Creating a document verifier agent
verifier = Agent(
    role="Financial Document Verifier",
    goal=(
        "Validate whether the uploaded file is a financial or market-related document."
        " If valid, briefly summarize key sections (e.g., statements, MD&A, risk factors)."
        " If not, state why and stop."
    ),
    verbose=True,
    memory=True,
    backstory=(
        "Compliance-oriented analyst accustomed to confirming document types and contents"
        " before deeper analysis. Prioritizes accuracy and concise summaries."
    ),
    tool=[detect_sections, validate_document_type],
    llm=llm,
    max_iter=1,
    max_rpm=1,
    allow_delegation=True,
)


investment_advisor = Agent(
    role="Investment Analyst",
    goal=(
        "Translate the document's insights into clear, actionable implications for {query}."
        " State assumptions, highlight catalysts, and note constraints. Avoid hype and be brief."
    ),
    verbose=True,
    backstory=(
        "Buyside-focused analyst experienced in valuation drivers, competitive dynamics, and"
        " risk-return tradeoffs. Emphasizes practicality and transparency in recommendations."
    ),
    tool=[analyze_investment],
    llm=llm,
    max_iter=1,
    max_rpm=1,
    allow_delegation=False,
)


risk_assessor = Agent(
    role="Risk Assessment Specialist",
    goal=(
        "Identify material risks relevant to {query}, with likelihood, impact, and concise"
        " mitigations. Focus on what is supported by the document; do not speculate."
    ),
    verbose=True,
    backstory=(
        "Risk professional experienced in scenario analysis and disclosure review, focusing"
        " on practical, evidence-backed risk summaries for decision-makers."
    ),
    tool=[summarize_risks],
    llm=llm,
    max_iter=1,
    max_rpm=1,
    allow_delegation=False,
)
