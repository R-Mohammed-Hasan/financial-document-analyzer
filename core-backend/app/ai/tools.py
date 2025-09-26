"""
AI Tools for financial document analysis and web search.

This module provides CrewAI tools for financial document processing and analysis.
"""

import os
import json
import re
from typing import List, Dict
from langchain_openai import ChatOpenAI
from crewai.tools import tool
from langchain_community.document_loaders import PyPDFLoader
from pydantic import BaseModel, Field, ValidationError
from utils.sanitize import sanitize_string


# Financial Metrics Schema
class FinancialMetrics(BaseModel):
    revenue: str = Field(default="", description="Reported revenue")
    eps: str = Field(default="", description="Earnings per share")
    ebitda: str = Field(default="", description="EBITDA")
    gross_margin: str = Field(default="", description="Gross margin")
    operating_margin: str = Field(default="", description="Operating margin")
    guidance: str = Field(default="", description="Forward-looking guidance")


@tool("Read financial PDF")
def read_financial_pdf(path: str = "data/sample.pdf") -> str:
    """Read and return text from a financial PDF."""
    try:
        loader = PyPDFLoader(path)
        docs = loader.load()
        return "\n".join(sanitize_string(d.page_content) for d in docs)
    except Exception as e:
        return f"Error reading PDF: {str(e)}"


@tool("Summarize financial overview")
def summarize_financial_overview(text: str, max_sentences: int = 5) -> str:
    """Produce a professional executive overview using OpenAI."""
    if not text:
        return "No content to summarize."

    prompt = (
        "You are an equity research analyst. Write a concise, professional executive overview "
        "of the following financial document text. Keep it factual and decision-ready.\n\n"
        f"Requirements:\n- 2 to {max(2, min(5, int(max_sentences)))} sentences overview\n"
        "- Then up to 5 bullets for Key Drivers/Highlights with figures if present\n"
        "- Mention period context (quarter/year) if inferable\n"
        "- Avoid hype/speculation; use numbers when available\n\n"
        f"Document Text (truncated):\n{text[:20000]}"
    )

    try:
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_OVERVIEW_MODEL", "gpt-3.5-turbo"), temperature=0.3
        )
        resp = llm.invoke(prompt)
        content = getattr(resp, "content", None)
        if isinstance(content, str) and content.strip():
            return content.strip()
    except Exception:
        pass

    # Fallback heuristic
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    head = " ".join(sentences[: max(1, int(max_sentences))])
    return head


@tool("Extract key financial metrics")
def extract_key_metrics(text: str) -> Dict[str, str]:
    """Extract headline financial metrics using LLM with fallback."""
    if not text:
        return FinancialMetrics().dict()

    prompt = (
        "Extract key headline financial metrics from the following financial report. "
        "Return ONLY a JSON object with keys: revenue, eps, ebitda, gross_margin, "
        "operating_margin, guidance. Use raw strings from the text (do not invent numbers). "
        "If missing, leave as an empty string.\n\n"
        f"Text:\n{text[:20000]}"
    )

    try:
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_METRICS_MODEL", "gpt-3.5-turbo"),
            temperature=0,
        )
        resp = llm.invoke(prompt)
        content = getattr(resp, "content", "").strip()

        if not content:
            raise ValueError("Empty LLM response")

        data = json.loads(content)
        metrics = FinancialMetrics(**data)
        return metrics.dict()

    except (json.JSONDecodeError, ValidationError, Exception):
        # Fallback to regex heuristics
        return _heuristic_extract_key_metrics(text)


def _heuristic_extract_key_metrics(text: str) -> Dict[str, str]:
    """Fallback regex-based heuristic extraction."""
    patterns = {
        "revenue": r"revenue[^$\d]*(\$?\d[\d,\.]*)",
        "eps": r"EPS[^$\d]*(\$?\d[\d,\.]*)",
        "ebitda": r"EBITDA[^$\d]*(\$?\d[\d,\.]*)",
        "gross_margin": r"gross margin[^$\d]*(\d{1,3}\.?\d*%)",
        "operating_margin": r"operating margin[^$\d]*(\d{1,3}\.?\d*%)",
        "guidance": r"guidance[^.]*\.",
    }

    results = {}
    for key, pat in patterns.items():
        m = re.search(pat, text, re.IGNORECASE)
        results[key] = m.group(1) if m else ""
    return {**FinancialMetrics().dict(), **results}


@tool("Detect financial sections")
def detect_sections(text: str) -> List[str]:
    """Detect present sections in financial document."""
    if not text:
        return []

    prompt = (
        "Detect which of these sections are present in the provided financial document text: "
        "['Income Statement','Balance Sheet','Cash Flow','MD&A','Risk Factors','Notes','Guidance/Outlook']. "
        "Return a JSON array of section names that appear to be present. JSON only.\n\n"
        f"Text (truncated):\n{text[:20000]}"
    )

    try:
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_SECTIONS_MODEL", "gpt-3.5-turbo"), temperature=0
        )
        resp = llm.invoke(prompt)
        content = getattr(resp, "content", None)
        if isinstance(content, str) and content.strip():
            try:
                arr = json.loads(content)
                if isinstance(arr, list):
                    cleaned = [str(x) for x in arr if isinstance(x, (str,))]
                    return cleaned
            except Exception:
                pass
    except Exception:
        pass

    return _heuristic_detect_sections(text)


def _heuristic_detect_sections(text: str) -> List[str]:
    """Fallback heuristic section detection."""
    if not text:
        return []

    candidates = {
        "Income Statement": [
            r"consolidated statements? of operations",
            r"income statement",
        ],
        "Balance Sheet": [r"balance sheet", r"statements? of financial position"],
        "Cash Flow": [r"cash flows?", r"statements? of cash flows"],
        "MD&A": [r"management\'?s? discussion and analysis", r"md&a"],
        "Risk Factors": [r"risk factors"],
        "Notes": [r"notes to (?:the )?consolidated financial statements"],
        "Guidance/Outlook": [r"guidance", r"outlook"],
    }

    present = []
    lowered = text.lower()
    for name, patterns in candidates.items():
        for pat in patterns:
            if re.search(pat, lowered):
                present.append(name)
                break
    return present


@tool("Validate document type")
def validate_document_type(text: str) -> str:
    """Classify if a document is financial/market related."""
    if not text:
        return "non-financial: empty content"

    lowered = text.lower()
    positive_signals = [
        r"consolidated statements?",
        r"income statement",
        r"balance sheet",
        r"cash flows?",
        r"management\'?s? discussion and analysis",
        r"risk factors",
        r"earnings per share|eps",
        r"revenue",
    ]
    negative_signals = [
        r"novel|fiction|poem|recipe|menu",
        r"user manual|installation guide",
    ]

    score = 0
    for pat in positive_signals:
        if re.search(pat, lowered):
            score += 1
    for pat in negative_signals:
        if re.search(pat, lowered):
            score -= 2

    label = (
        "financial"
        if score >= 2
        else "likely financial" if score == 1 else "non-financial"
    )
    return f"{label} (score={score})"


@tool("Analyze investment implications")
def analyze_investment(financial_document_text: str) -> str:
    """Provide investment implications analysis."""
    if not financial_document_text:
        return "No content to analyze."

    positives = len(
        re.findall(
            r"beat|above guidance|ahead of|strong|record", financial_document_text, re.I
        )
    )
    negatives = len(
        re.findall(
            r"miss|below guidance|weak|decline|headwinds|shortfall",
            financial_document_text,
            re.I,
        )
    )

    tone = "neutral"
    if positives - negatives >= 2:
        tone = "constructively positive"
    elif negatives - positives >= 2:
        tone = "cautiously negative"

    return (
        "Investment implications (heuristic): tone="
        + tone
        + "; watch guidance, margins, and cash flow for confirmation."
    )


@tool("Summarize key risks")
def summarize_risks(financial_document_text: str) -> str:
    """Summarize key risks from financial document."""
    if not financial_document_text:
        return "No content to evaluate."

    prompt = (
        "You are a risk analysis assistant. Extract and summarize the top risks from the provided "
        "financial document text. Return a structured, concise output in plain text with these sections:\n\n"
        "Overview:\n- 1-2 sentences\n\n"
        "Top Risks:\n- 3-6 bullets; each bullet includes Risk Area, Evidence (quote/phrase), Likelihood (L/M/H), Impact (L/M/H)\n\n"
        "Mitigations:\n- 2-4 bullets\n\n"
        "Be factual and avoid speculation beyond what's implied by the text.\n\n"
        f"Document Text (truncated):\n{financial_document_text[:20000]}"
    )

    try:
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_RISK_MODEL", "gpt-3.5-turbo"), temperature=0.3
        )
        resp = llm.invoke(prompt)
        content = getattr(resp, "content", None)
        if isinstance(content, str) and content.strip():
            return content.strip()
    except Exception:
        pass

    return _heuristic_risk_summary(financial_document_text)


def _heuristic_risk_summary(financial_document_text: str) -> str:
    """Fallback heuristic risk summary."""
    if not financial_document_text:
        return "No content to evaluate."

    lowered = financial_document_text.lower()
    buckets = {
        "Demand/Volume": ["demand", "volume", "orders"],
        "Pricing/Margin": ["pricing", "margin", "cost inflation", "input costs"],
        "Supply/Operations": ["supply", "logistics", "capacity", "production"],
        "Regulatory/Legal": ["regulatory", "compliance", "litigation", "investigation"],
        "FX/Macro": ["foreign exchange", "fx", "macro", "rates"],
    }

    hits = []
    for name, terms in buckets.items():
        for t in terms:
            if t in lowered:
                hits.append(name)
                break

    if not hits:
        return "No explicit risks detected by heuristics; review MD&A and risk factors."

    unique = ", ".join(sorted(set(hits)))
    return f"Key risk areas flagged: {unique}. Assess likelihood (L/M/H) and impact (L/M/H) based on disclosure specifics."
