"""
AI Task definitions for financial document analysis using CrewAI.

This module defines CrewAI tasks for orchestrating the financial analysis workflow.
"""

from crewai import Task
from ai.agents import financial_analyst, verifier, investment_advisor, risk_assessor

# Task 1: Document Verification
verify_document = Task(
    description=(
        "Verify if the uploaded document is a financial or market-related document. "
        "If valid, provide a brief summary of key sections. If not, state why and stop."
    ),
    expected_output=(
        "A clear statement on document validity with brief summary if valid, "
        "or explanation if invalid."
    ),
    agent=verifier,
    context=[],
)

# Task 2: Financial Analysis
analyze_financials = Task(
    description=(
        "Perform comprehensive financial analysis based on the user's query. "
        "Extract key figures, trends, and drivers from the document. "
        "Provide evidence-based insights without speculation."
    ),
    expected_output=(
        "Concise, decision-ready financial analysis with key metrics, "
        "trends, and insights tailored to the query."
    ),
    agent=financial_analyst,
    context=[verify_document],
)

# Task 3: Investment Analysis
investment_analysis = Task(
    description=(
        "Translate document insights into actionable investment implications. "
        "State assumptions, highlight catalysts, and note constraints. "
        "Be brief and avoid hype."
    ),
    expected_output=(
        "Clear, actionable investment implications with assumptions, "
        "catalysts, and constraints."
    ),
    agent=investment_advisor,
    context=[analyze_financials],
)

# Task 4: Risk Assessment
assess_risks = Task(
    description=(
        "Identify material risks relevant to the query with likelihood, "
        "impact, and concise mitigations. Focus on document-supported risks."
    ),
    expected_output=(
        "Structured risk assessment with likelihood, impact, and mitigations "
        "based on document evidence."
    ),
    agent=risk_assessor,
    context=[analyze_financials],
)
