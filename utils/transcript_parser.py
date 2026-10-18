"""Parse RAM (Resource Allocation Meeting) transcript markdown files.

Transcripts live in the UC Volume at config.TRANSCRIPT_VOLUME and follow
this structure:

    # Resource Allocation Meeting (RAM) - New Project Intake
    **Project:** <name>
    **Project ID:** <id>
    **Meeting date:** <date>
    **Decision:** <text>
    ## Participants
    - Name - Role
    ## HH:MM - Section Title
    **Speaker:** dialogue ...
"""
import re
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class TranscriptSection:
    time: str
    title: str
    content: str
    speakers: List[str] = field(default_factory=list)


@dataclass
class ParsedTranscript:
    project_name: str = ""
    project_id: str = ""
    meeting_date: str = ""
    decision: str = ""
    participants: List[Dict[str, str]] = field(default_factory=list)
    sections: List[TranscriptSection] = field(default_factory=list)
    raw_text: str = ""

    # ------------------------------------------------------------------
    # Derived helpers used by the search and UI layers
    # ------------------------------------------------------------------
    @property
    def search_context(self) -> str:
        """All discussion text concatenated for similarity search."""
        parts = [self.project_name]
        for sec in self.sections:
            parts.append(sec.content)
        return " ".join(parts)

    @property
    def scope_text(self) -> str:
        for s in self.sections:
            if "scope" in s.title.lower():
                return s.content
        return ""

    @property
    def estimate_text(self) -> str:
        for s in self.sections:
            if "estimate" in s.title.lower() or "comparison" in s.title.lower():
                return s.content
        return ""

    @property
    def action_items(self) -> str:
        for s in self.sections:
            if "decision" in s.title.lower() or "action" in s.title.lower():
                return s.content
        return ""


def parse_transcript(text: str) -> ParsedTranscript:
    """Parse a RAM transcript markdown string into structured data."""
    result = ParsedTranscript(raw_text=text)
    lines = text.strip().split("\n")

    # ---- header metadata ----
    for line in lines[:15]:
        stripped = line.strip().rstrip("  ")
        if stripped.startswith("**Project:**"):
            result.project_name = stripped.replace("**Project:**", "").strip()
        elif stripped.startswith("**Project ID:**"):
            result.project_id = stripped.replace("**Project ID:**", "").strip()
        elif stripped.startswith("**Meeting date:**"):
            result.meeting_date = stripped.replace("**Meeting date:**", "").strip()
        elif stripped.startswith("**Decision:**"):
            result.decision = stripped.replace("**Decision:**", "").strip()

    # ---- participants ----
    in_participants = False
    for line in lines:
        if line.strip() == "## Participants":
            in_participants = True
            continue
        if in_participants:
            if line.startswith("##"):
                in_participants = False
                continue
            m = re.match(r"^- (.+?) - (.+)$", line.strip())
            if m:
                result.participants.append(
                    {"name": m.group(1).strip(), "role": m.group(2).strip()}
                )

    # ---- timed sections ----
    sec_re = re.compile(r"^## (\d{2}:\d{2}) - (.+)$")
    cur: TranscriptSection | None = None
    for line in lines:
        m = sec_re.match(line.strip())
        if m:
            if cur:
                result.sections.append(cur)
            cur = TranscriptSection(time=m.group(1), title=m.group(2), content="")
            continue
        if cur is not None and line.strip():
            spk = re.match(r"^\*\*(.+?)\*\*:?\s*(.*)$", line.strip())
            if spk:
                name = spk.group(1)
                if name not in cur.speakers:
                    cur.speakers.append(name)
                cur.content += spk.group(2) + " "
            elif not line.startswith("#"):
                cur.content += line.strip() + " "
    if cur:
        result.sections.append(cur)

    return result
