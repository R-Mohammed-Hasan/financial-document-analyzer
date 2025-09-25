"""Tools for financial document analysis and web search."""

## Importing libraries and files
import re
from typing import List, Dict
import os
import json
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from crewai_tools import SerperDevTool
from crewai.tools import tool
from langchain_community.document_loaders import PyPDFLoader
from pydantic import BaseModel, Field, ValidationError
from utils import clean_page_content

load_dotenv()

## Creating search tool
search_tool = SerperDevTool()


## Creating pdf reader tools (annotation-based)
@tool("Read financial PDF (default TSLA)")
def read_financial_pdf(path: str = r"data\TSLA-Q2-2025-Update.pdf") -> str:
    """Read and return text from a financial PDF. Path optional; defaults to TSLA sample."""
    loader = PyPDFLoader(path)
    docs = loader.load()
    return "\n".join(clean_page_content(d.page_content) for d in docs)


# CrewAI-compatible tool function
@tool("Read PDF document")
def read_pdf(path: str = "data/sample.pdf") -> str:
    """Read and return text content from a PDF at the given path."""
    loader = PyPDFLoader(path)
    docs = loader.load()

    return "\n".join(clean_page_content(d.page_content) for d in docs)


# -------------------- Analysis helpers (CrewAI tools) --------------------


@tool("Summarize financial overview")
def summarize_financial_overview(text: str, max_sentences: int = 5) -> str:
    """Produce a professional executive overview using OpenAI; fallback to heuristic.

    Output: 2-5 sentences plus up to 5 bullets for key drivers and figures.
    """
    if not text:
        return "No content to summarize."

    prompt = (
        "You are an equity research analyst. Write a concise, professional executive overview "
        "of the following financial document text. Keep it factual and decision-ready.\n\n"
        "Requirements:\n"
        f"- 2 to {max(2, min(5, int(max_sentences)))} sentences overview\n"
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

    # Heuristic fallback: take first N sentences from the start
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    head = " ".join(sentences[: max(1, int(max_sentences))])
    return head


def _heuristic_extract_key_metrics(text: str) -> Dict[str, str]:
    if not text:
        return {}

    def find(patterns: List[str]) -> str:
        for p in patterns:
            m = re.search(p, text, flags=re.IGNORECASE)
            if m:
                return m.group(0)
        return ""

    revenue = find(
        [
            r"revenue[^\n]{0,60}?\$?\s?\d{1,3}(?:[,\d]{0,3})*(?:\.\d+)?\s?(?:billion|million|k|m|bn)?",
            r"total\s+sales[^\n]{0,60}?\$?\s?\d{1,3}(?:[,\d]{0,3})*(?:\.\d+)?\s?(?:billion|million|k|m|bn)?",
        ]
    )
    eps = find(
        [
            r"(?:eps|earnings per share)[^\n]{0,40}?\$?\s?-?\d+(?:\.\d+)?",
        ]
    )
    ebitda = find(
        [
            r"ebitda[^\n]{0,60}?\$?\s?\d{1,3}(?:[,\d]{0,3})*(?:\.\d+)?",
        ]
    )
    gross_margin = find(
        [
            r"gross\s+margin[^\n]{0,40}?\d{1,3}\.?\d?%",
        ]
    )
    operating_margin = find(
        [
            r"operating\s+margin[^\n]{0,40}?\d{1,3}\.?\d?%",
        ]
    )
    guidance = find(
        [
            r"guidance[^\n]{0,160}",
            r"outlook[^\n]{0,160}",
        ]
    )
    return {
        "revenue": revenue,
        "eps": eps,
        "ebitda": ebitda,
        "gross_margin": gross_margin,
        "operating_margin": operating_margin,
        "guidance": guidance,
    }


# Define schema for structured extraction
class FinancialMetrics(BaseModel):
    revenue: str = Field(default="", description="Reported revenue")
    eps: str = Field(default="", description="Earnings per share")
    ebitda: str = Field(default="", description="EBITDA")
    gross_margin: str = Field(default="", description="Gross margin")
    operating_margin: str = Field(default="", description="Operating margin")
    guidance: str = Field(default="", description="Forward-looking guidance")


def _heuristic_extract_key_metrics(text: str) -> Dict[str, str]:
    """Fallback regex-based heuristic extraction (simplified example)."""
    import re

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


@tool("Extract key financial metrics")
def extract_key_metrics(text: str) -> Dict[str, str]:
    """Extract headline financial metrics using LLM with fallback to regex heuristics."""

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
        # fallback to regex heuristics
        return _heuristic_extract_key_metrics(text)


def _heuristic_detect_sections(text: str) -> List[str]:
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


@tool("Detect financial sections")
def detect_sections(text: str) -> List[str]:
    """Use OpenAI to detect present sections; fallback to heuristic detection."""
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
            import json as _json

            try:
                arr = _json.loads(content)
                if isinstance(arr, list):
                    cleaned = [str(x) for x in arr if isinstance(x, (str,))]
                    return cleaned
            except Exception:
                pass
    except Exception:
        pass
    return _heuristic_detect_sections(text)


@tool("Validate document type: financial or not")
def validate_document_type(text: str) -> str:
    """Heuristically classify if a document is financial/market related."""
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


## Creating Investment Analysis Tool (annotation-based)
@tool("Analyze investment implications")
def analyze_investment(financial_document_text: str) -> str:
    """Provide a brief, actionable read of implications for investors (heuristic)."""
    if not financial_document_text:
        return "No content to analyze."

    # Pull some key phrases for a quick heuristic read
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


## Creating Risk Assessment Tool (annotation-based)
def _heuristic_risk_summary(financial_document_text: str) -> str:
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


@tool("Summarize key risks")
def summarize_risks(financial_document_text: str) -> str:
    """Use OpenAI (via langchain_openai) to produce a formatted risk summary; fallback to heuristics."""
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
