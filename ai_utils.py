"""
ai_utils.py — AI-powered file explanation and forensic chatbot.

Provider : Groq (free tier)
Model    : llama-3.3-70b-versatile
Install  : pip install groq
Key      : set GROQ_API_KEY environment variable
           Get a free key at https://console.groq.com
"""

import json
import os


try:
    from groq import Groq
    _client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    _client = None

MODEL = "llama-3.3-70b-versatile"

# ---------------------------------------------------------------------------
# System prompt for the forensic chatbot
# ---------------------------------------------------------------------------
CHATBOT_SYSTEM = """You are ForenScan AI, an expert digital forensics assistant embedded inside the ForenScan file analysis tool.

Your role is to:
- Explain scan results in plain English for analysts at any skill level
- Answer questions about file types, magic numbers, entropy, MIME types, anomalies, and hash values
- Give actionable guidance on suspicious findings (e.g. "what does high entropy mean?", "is this file dangerous?")
- Explain forensic concepts clearly without unnecessary jargon
- Be concise but thorough — use bullet points where helpful

You have access to the current scan results below. Always ground your answers in the actual data provided.
Never fabricate hash values, risk levels, or file details. If the data does not contain something, say so.
Keep responses focused on the forensic context."""


def _build_scan_context(results: list[dict]) -> str:
    """Serialise scan results into a compact context string for the LLM."""
    lines = [f"SCAN CONTAINS {len(results)} FILE(S)\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"--- File {i}: {r.get('filename', 'unknown')} ---")
        lines.append(f"  Detected type : {r.get('detected_type', 'UNKNOWN')}")
        lines.append(f"  MIME type     : {r.get('mime_type', '—')}")
        lines.append(f"  Declared ext  : .{r.get('declared_ext', '?')}")
        lines.append(f"  Risk level    : {r.get('risk_level', 'UNKNOWN')}")
        lines.append(f"  File size     : {r.get('file_size', '—')} bytes")
        lines.append(f"  Anomaly flag  : {'YES' if r.get('anomaly_flag') else 'No'}")
        if r.get('anomaly_reason'):
            lines.append(f"  Anomaly reason: {r['anomaly_reason']}")
        lines.append(f"  Entropy       : {r.get('entropy', '—')}")
        lines.append(f"  MD5           : {r.get('md5_hash', '—')}")
        lines.append(f"  SHA-256       : {r.get('sha256_hash', '—')}")
        lines.append(f"  Footer valid  : {r.get('footer_valid')}")
        if r.get('yara_hits'):
            lines.append(f"  YARA hits     : {r['yara_hits']}")
        if r.get('error'):
            lines.append(f"  Error         : {r['error']}")
        lines.append("")
    return "\n".join(lines)


def _check_available() -> str | None:
    """Return an error string if Groq is not usable, else None."""
    if not GROQ_AVAILABLE:
        return "Groq library not installed. Run: pip install groq"
    if not os.environ.get("GROQ_API_KEY"):
        return "GROQ_API_KEY not set. Get a free key at https://console.groq.com"
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def explain_scan(results: list[dict]) -> dict:
    """
    Generate a structured plain-English explanation of the scan.

    Returns:
        {
          "overview": str,
          "risk_summary": str,
          "file_explanations": [{"filename", "plain_english", "key_indicators"}],
          "recommendations": [str]
        }
        or {"error": str} on failure.
    """
    err = _check_available()
    if err:
        return {"error": err}

    scan_ctx = _build_scan_context(results)

    prompt = f"""You are a digital forensics expert. Analyse the scan data below and respond ONLY with valid JSON — no markdown fences, no preamble. Use exactly this schema:

{{
  "overview": "2-3 sentence plain-English summary of what was found",
  "risk_summary": "one sentence risk verdict",
  "file_explanations": [
    {{
      "filename": "...",
      "plain_english": "What this file is and why it has the assigned risk level, in 1-2 sentences",
      "key_indicators": ["indicator 1", "indicator 2"]
    }}
  ],
  "recommendations": ["action 1", "action 2", "action 3"]
}}

SCAN DATA:
{scan_ctx}"""

    try:
        response = _client.chat.completions.create(
            model=MODEL,
            max_tokens=1500,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()

        # Strip accidental markdown fences if model adds them anyway
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        return json.loads(raw)

    except json.JSONDecodeError as e:
        return {"error": f"Could not parse AI response as JSON: {e}"}
    except Exception as e:
        return {"error": str(e)}


def chat(
    user_message: str,
    history: list[dict],
    results: list[dict],
) -> str:
    """
    Single-turn chat with conversation history.

    Parameters
    ----------
    user_message : str   — the analyst's latest question
    history      : list  — previous turns [{"role": "user"|"assistant", "content": str}]
    results      : list  — current scan results injected as system context

    Returns
    -------
    str — assistant reply, or string starting with "ERROR:" on failure
    """
    err = _check_available()
    if err:
        return f"ERROR: {err}"

    scan_ctx = _build_scan_context(results)
    system_with_ctx = f"{CHATBOT_SYSTEM}\n\nCURRENT SCAN DATA:\n{scan_ctx}"

    messages = [{"role": "system", "content": system_with_ctx}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    try:
        response = _client.chat.completions.create(
            model=MODEL,
            max_tokens=800,
            temperature=0.3,
            messages=messages,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"ERROR: {e}"