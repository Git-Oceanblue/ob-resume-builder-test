import re
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

DEFAULT_SECTIONS = ["header", "summary", "experience", "education", "skills", "certifications"]

WORK_DATE_RANGE_PATTERN = re.compile(
    r"(?i)\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
    r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(?:19|20)\d{2}\s*[-–—]\s*"
    r"(?:present|current|till\s+date|"
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
    r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(?:19|20)\d{2})\b"
)

SECTION_HEADER_ALIASES = {
    "summary": [
        "summary",
        "professional summary",
        "profile",
        "professional profile",
        "career summary",
        "summary of qualifications",
        "objective",
        "career objective"
    ],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "work history"
    ],
    "education": [
        "education",
        "academic background",
        "educational background",
        "qualifications"
    ],
    "skills": [
        "skills",
        "skill set",
        "technical skills",
        "technical skill set",
        "technical proficiency",
        "technical proficiencies",
        "key skills",
        "core competencies",
        "competencies",
        "skills summary"
    ],
    "certifications": [
        "certifications",
        "certification",
        "licenses",
        "certificates",
        "professional certifications"
    ]
}

def chunk_resume_from_bold_headings(raw_text: str, expected_sections: Optional[List[str]] = None) -> Dict[str, Any]:

    if raw_text is None:
        raw_text = ""

    expected_sections = expected_sections or DEFAULT_SECTIONS

    # We never "infer" or rename. Keys remain exactly as expected_sections.
    output: Dict[str, Optional[str]] = {sec: None for sec in expected_sections if sec != "header"}

    # If you want "header" behavior like your current code:
    # header = text before first detected section header.
    header_text: Optional[str] = None

    # Detect section headers (line-based, strict)
    matches = _detect_headers(raw_text, expected_sections=[s for s in expected_sections if s != "header"])

    # No sections found -> Uncategorized
    if not matches:
        unc = raw_text.strip()
        result: Dict[str, Any] = {
            "Uncategorized": unc if unc else None,
            "integrity_check": {
                "Uncategorized": {
                    "raw_chars": len(raw_text),
                    "extracted_chars": len(unc),
                    "status": "ok" if len(unc) == len(raw_text.strip()) else "warn"
                }
            }
        }
        if result["integrity_check"]["Uncategorized"]["status"] != "ok":
            result["integrity_warning"] = [
                "Uncategorized extraction differs from trimmed raw text length (expected due to trimming)."
            ]
        return result

    # Sort + de-dup
    matches = sorted(matches, key=lambda m: m["line_start"])
    matches = _dedupe_matches(matches)

    # Heuristic: infer experience start if header is absent but job date ranges exist.
    if "experience" in expected_sections and not any(m["section_key"] == "experience" for m in matches):
        inferred_experience = _infer_experience_match(raw_text, matches)
        if inferred_experience:
            matches.append(inferred_experience)
            matches = sorted(matches, key=lambda m: m["line_start"])
            matches = _dedupe_matches(matches)
            logger.info("Inferred experience section from job-date patterns.")

    # Header section = before first heading
    first = matches[0]
    header_slice = raw_text[:first["line_start"]]
    header_text = header_slice.strip()
    # include header if requested
    if "header" in expected_sections:
        output_header = header_text if header_text else None
    else:
        output_header = None

    integrity_check: Dict[str, Dict[str, Any]] = {}
    integrity_warnings: List[str] = []

    # Slice each section
    for i, m in enumerate(matches):
        sec = m["section_key"]

        start = m["content_start"]  # start AFTER header line (keeps content intact)
        end = matches[i + 1]["line_start"] if i + 1 < len(matches) else len(raw_text)

        raw_slice = raw_text[start:end]
        extracted = raw_slice.strip()
        output[sec] = extracted if extracted else None

        raw_trim = raw_slice.strip()
        status = "ok" if len(extracted) == len(raw_trim) else "warn"

        integrity_check[sec] = {
            "raw_slice_chars": len(raw_slice),
            "raw_slice_trimmed_chars": len(raw_trim),
            "extracted_chars": len(extracted),
            "status": status
        }

        # Boundary sanity: if warn, keep warning (no destructive adjustments)
        if status != "ok":
            integrity_warnings.append(
                f"{sec}: extracted_chars({len(extracted)}) != raw_slice_trimmed_chars({len(raw_trim)}). "
                "Possible boundary mismatch."
            )

    result: Dict[str, Any] = {}
    if "header" in expected_sections:
        result["header"] = output_header
    # add remaining sections in expected order
    for sec in expected_sections:
        if sec == "header":
            continue
        result[sec] = output.get(sec)

    result["integrity_check"] = integrity_check
    if integrity_warnings:
        result["integrity_warning"] = integrity_warnings

    return result


def _detect_headers(raw_text: str, expected_sections: List[str]) -> List[Dict[str, Any]]:
    """
    Strict-but-flexible header detection:
    - Matches only standalone heading lines
    - Supports common resume heading aliases
    This prevents false splits like 'Certified Professional Scrum Master ...'
    """
    bullet_chars = r"\u2022\u2023\u25E6\u2043\u2219\u00B7"
    line_prefix = rf"\s*(?:\*{{1,2}}\s*)?(?:[-*{bullet_chars}]+\s*)?(?:\d+\s*[\.\)]\s*)?"

    section_patterns: List[Dict[str, Any]] = []
    for sec in expected_sections:
        aliases = SECTION_HEADER_ALIASES.get(sec, [sec])
        alias_pattern = "|".join(re.escape(alias.strip()) for alias in aliases if alias and alias.strip())
        if not alias_pattern:
            continue

        section_patterns.append({
            "section_key": sec,
            # Standalone line heading: "Summary", "Summary:", "1) Summary", "**Summary**"
            "standalone": re.compile(
                rf"^{line_prefix}(?:{alias_pattern})\s*(?:[:|\-])?(?:\s*\*{{1,2}})?\s*$",
                re.IGNORECASE
            ),
            # Inline heading: "Education: Bachelor of Technology ..."
            "inline": re.compile(
                rf"^{line_prefix}(?:{alias_pattern})\s*[:|\-]\s*(?P<content>\S.*?)(?:\s*\*{{1,2}})?\s*$",
                re.IGNORECASE
            )
        })

    matches = []
    pos = 0
    for line in raw_text.splitlines(keepends=True):
        line_start = pos
        line_end = pos + len(line)
        line_no_newline = line.rstrip("\r\n")

        for pattern_info in section_patterns:
            inline_match = pattern_info["inline"].match(line_no_newline)
            if inline_match:
                matches.append({
                    "section_key": pattern_info["section_key"],
                    "line_start": line_start,
                    "line_end": line_end,
                    # Include text after delimiter on same line in section content.
                    "content_start": line_start + inline_match.start("content")
                })
                break

            if pattern_info["standalone"].match(line_no_newline):
                matches.append({
                    "section_key": pattern_info["section_key"],
                    "line_start": line_start,
                    "line_end": line_end,
                    # content starts after full header line (including newline)
                    "content_start": line_end
                })
                break

        pos = line_end

    if matches:
        logger.info(f"Detected {len(matches)} headers: " + ", ".join([m["section_key"] for m in matches]))
    else:
        logger.info("No strict section headers detected.")

    return matches


def _dedupe_matches(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicates/overlaps.
    - Keep earliest match when overlaps occur.
    - If same section repeats back-to-back with no content, keep the first.
    """
    if not matches:
        return []

    out = [matches[0]]
    for m in matches[1:]:
        prev = out[-1]

        # overlap -> skip
        if m["line_start"] < prev["line_end"]:
            continue

        # very close duplicate same header -> skip
        if m["section_key"] == prev["section_key"] and (m["line_start"] - prev["line_start"]) < 5:
            continue

        out.append(m)

    return out


def _infer_experience_match(raw_text: str, matches: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Infer experience section when explicit header is missing.
    Uses common employment date-range patterns (e.g., 'Aug 2024 - Current').
    """
    if not matches:
        return None

    # Only infer when other structured sections exist.
    if not any(m["section_key"] in {"skills", "education"} for m in matches):
        return None

    # Start searching after first detected heading line to avoid header/contact text.
    lower_bound = min(m["line_end"] for m in matches)

    # Prefer inferring experience before education/certifications if those are explicitly detected.
    trailing_bounds = [
        m["line_start"] for m in matches if m["section_key"] in {"education", "certifications"}
    ]
    upper_bound = min(trailing_bounds) if trailing_bounds else len(raw_text)

    pos = 0
    candidate_lines: List[Dict[str, int]] = []
    for line in raw_text.splitlines(keepends=True):
        line_start = pos
        line_end = pos + len(line)
        line_no_newline = line.rstrip("\r\n")

        if line_start >= lower_bound and line_start < upper_bound:
            if WORK_DATE_RANGE_PATTERN.search(line_no_newline):
                candidate_lines.append({"line_start": line_start, "line_end": line_end})

        pos = line_end

    if not candidate_lines:
        return None

    first = candidate_lines[0]
    return {
        "section_key": "experience",
        "line_start": first["line_start"],
        "line_end": first["line_end"],
        # Keep the line itself (job title + date range often on same line).
        "content_start": first["line_start"]
    }

# ------------------------------------------------------------------
# BACKWARD-COMPATIBILITY UTILITY (USED BY OTHER MODULES)
# ------------------------------------------------------------------

BULLET_PREFIX_PATTERN = re.compile(
    r'^\s*(?:--+|[-*\u2022\u2023\u25E6\u2043\u2219\u00B7]+)(?:\s+|(?=[A-Za-z0-9]))'
)

def strip_bullet_prefix(text: str) -> str:
    """
    Remove leading bullet symbols from a line of text.

    NOTE:
    - This function is kept for backward compatibility.
    - The new chunking logic DOES NOT depend on it.
    - Other modules (ai_parser, etc.) still import it.
    """
    stripped = text
    while True:
        new_text = BULLET_PREFIX_PATTERN.sub('', stripped, count=1)
        if new_text == stripped:
            break
        stripped = new_text
    return stripped.lstrip()
