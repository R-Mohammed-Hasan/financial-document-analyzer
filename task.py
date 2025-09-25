"""Task definitions for precise financial document analysis and verification."""

## Importing libraries and files
from crewai import Task

from agents import financial_analyst, verifier
from tools import (
    search_tool,
    read_pdf,
    summarize_financial_overview,
    extract_key_metrics,
    detect_sections,
    validate_document_type,
)

## Analyze financial document precisely
analyze_financial_document = Task(
    description=(
        "Analyze the provided financial document with respect to the user's query: {query}."
        " Extract only relevant facts, figures, and statements. Keep the response concise."
    ),
    expected_output=(
        "Short, structured output with: Overview (2-3 sentences), Key metrics (bullets),"
        " Opportunities (bullets), Risks (bullets), and a brief Answer addressing {query}."
    ),
    agent=financial_analyst,
    tools=[read_pdf, summarize_financial_overview, extract_key_metrics, search_tool],
    async_execution=False,
)

## Verify document type succinctly
verification = Task(
    description=(
        "Determine if the uploaded file appears to be a financial document. If yes, list"
        " detected sections briefly; if no, state the reason."
    ),
    expected_output=(
        "One-line classification (financial/non-financial) and up to 5 bullets of sections"
        " or reasons."
    ),
    agent=verifier,
    tools=[read_pdf, detect_sections, validate_document_type],
    async_execution=False,
)
