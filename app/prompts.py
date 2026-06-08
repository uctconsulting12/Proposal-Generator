"""Prompt construction for the proposal copilot.

The conversation moves through stages (questioning -> draft -> final). The
system prompt sets the role and context once; each turn then carries a
*control instruction* telling the model exactly what to produce next.
"""

from __future__ import annotations

import re

from .schemas import JDIntake

# Hard cap so even a 2000-char intro becomes a usable About Us paragraph.
_CONDENSED_INTRO_MAX_CHARS = 220
_CONDENSED_INTRO_MAX_SENTENCES = 2


def _condense_intro(intro: str) -> str:
    """Reduce a long company intro to its first 1-2 sentences.

    The model has shown it copies whatever full text we hand it, so when the
    user has *not* opted into the verbatim mode we never expose the original
    intro to the model — we shorten it here first. The trimmed text still
    carries the company's positioning vocabulary, which is enough for voice.
    """
    text = " ".join(intro.split())
    if not text:
        return ""
    # Split on sentence terminators but keep the punctuation attached.
    sentences = re.split(r"(?<=[.!?])\s+", text)
    short = " ".join(sentences[:_CONDENSED_INTRO_MAX_SENTENCES]).strip()
    if len(short) <= _CONDENSED_INTRO_MAX_CHARS:
        return short
    # Hard truncate on a word boundary if even two sentences are too long.
    cut = short[:_CONDENSED_INTRO_MAX_CHARS].rsplit(" ", 1)[0]
    return cut.rstrip(",;:- ") + "..."

_SYSTEM_INSTRUCTIONS = (
    "You are an expert Upwork Technical proposal writer. Your job is to help the "
    "freelancer WIN the job described below with a specific, persuasive "
    "proposal. Follow the instruction given in each turn exactly.\n\n"
    "IMPORTANT - use of past work: the section 'Retrieved Similar Past "
    "Projects' below contains real excerpts from the freelancer's previous "
    "proposals and delivered projects. Whenever a past project is genuinely "
    "similar to this job, you MUST call it out as concrete proof of relevant "
    "experience - name the project, what was delivered, the tech used, and the "
    "outcome - because demonstrating 'we have already done this' is what wins "
    "the job. Never invent experience: cite only projects that actually appear "
    "in the retrieved context, and if none is genuinely relevant, do not force "
    "a comparison - write a strong proposal based on the job requirements "
    "instead."
)

# The exact sentence the draft must end with so the user knows how to proceed.
APPROVAL_PROMPT_LINE = (
    'Reply "Approve" to generate the full proposal, or reply with changes to '
    "revise this draft."
)

# --- Control instructions, one per stage transition ----------------------
ASK_QUESTION = (
    "Ask the single most important clarifying question needed to write a strong "
    "proposal. Ask exactly one question, in one or two sentences. Do not write "
    "the proposal or a draft yet."
)

DRAFT_PROPOSAL = (
    "Using the job description, any answers gathered, and the retrieved past "
    "projects, write a SHORT draft proposal summary of about 130-200 words. "
    "Include: a one-line understanding of the client's goal; 3-5 bullet points "
    "of proposed scope; ONE line citing the most similar past project by name "
    "as proof of experience (e.g. 'We have delivered a closely similar project: "
    "<name> - <what/outcome>') - omit this line only if nothing relevant was "
    "retrieved; a rough timeline; and a one-line note on pricing/approach. Keep "
    "it brief - this is a preview for the user to approve. Finish with this "
    f"exact line on its own:\n{APPROVAL_PROMPT_LINE}"
)

FINAL_PROPOSAL = (
    "Write a COMPLETE, client-ready technical proposal in the structured, "
    "formal style of an enterprise RFP response. It must sound like a "
    "confident senior engineer / agency lead wrote it: specific, technical, "
    "client-focused, zero filler, zero AI-sounding phrases.\n\n"

    "FORMAT: Use exactly these 7 numbered sections in this order, each on "
    "its own line prefixed with '## ':\n"
    "## 1. Executive Summary\n"
    "## 2. Understanding of Requirements\n"
    "## 3. Our Proven Systems - Direct Portfolio Match\n"
    "## 4. Proposed Technical Architecture\n"
    "## 5. Data & Access Requirements\n"
    "## 6. Timeline - Delivery Plan\n"
    "## 7. Why Us\n\n"

    "Inside sections, use '### N.M Title' for subsections (e.g. '### 2.1 "
    "Detection & Tracking'). Use markdown tables (pipe syntax) for the "
    "portfolio map (Section 3), the architecture layer table (Section 4), "
    "and the deliverables table (Section 6).\n\n"

    "SECTION RULES:\n\n"

    "## 1. Executive Summary\n"
    "3 short paragraphs. (a) One paragraph positioning the company and the "
    "specific technical stack relevant to this job. (b) One paragraph "
    "claiming the capabilities with a bulleted list of 4-6 concrete "
    "capabilities you have already shipped that map to this brief. "
    "(c) One paragraph stating the proposed timeline and the split between "
    "integration of existing work vs. new development.\n\n"

    "## 2. Understanding of Requirements\n"
    "Open with 2-3 sentences restating the client's goal in technical terms. "
    "Then break the work into 3-5 logically-grouped pillars, each as a '### "
    "2.N Pillar Name' subsection with 3-5 bullet points underneath. End with "
    "a subsection '### 2.X What Your Brief Did Not Specify (But We Will "
    "Ask)' listing 4-6 concrete questions whose answers shape the build.\n\n"

    "## 3. Our Proven Systems - Direct Portfolio Match\n"
    "One short paragraph framing the table. Then a markdown table with "
    "EXACTLY three columns: 'System' | 'What It Does' | 'Maps To Your "
    "Requirement'. Pull every row from the retrieved past-project context "
    "below; do not invent system names. If fewer than 2 projects retrieved, "
    "use 3-4 capability rows grounded in real tools you would actually use. "
    "Close with 1-2 italicised sentences summarising the shared tech "
    "foundation.\n\n"

    "## 4. Proposed Technical Architecture\n"
    "One paragraph naming the pipeline shape (e.g. '7-layer pipeline'). "
    "Then a markdown table with 4 columns: 'Layer' | 'Component' | "
    "'Technology' | 'Status' (Status = 'Existing' / 'Adapted' / 'New "
    "build'). Add 1-2 '### 4.N' subsections covering the technically "
    "nuanced choices (the hardest engineering decision, plus a tech-stack "
    "summary list).\n\n"

    "## 5. Data & Access Requirements\n"
    "Use '### 5.1', '### 5.2', '### 5.3', '### 5.4' subsections covering "
    "domain-data needs, environment / infrastructure data, threshold or "
    "configuration definitions, and security / compliance questions. Each "
    "subsection: 3-5 bullets + a short italic 'Why this matters:' line.\n\n"

    "## 6. Timeline - Delivery Plan\n"
    "One paragraph naming the duration and number of phases. Then a "
    "markdown table with 3 columns: 'Phase' | 'Weeks' | 'Activities'. "
    "Follow it with a markdown deliverables table: 'Deliverable' | "
    "'Completion' (e.g. 'End of Week 5').\n\n"

    "## 7. Why Us\n"
    "Open with a sharp contrast paragraph (1-2 sentences). Then a markdown "
    "table with 2 columns: 'What Others Offer' | 'What We Deliver' (3-4 "
    "rows). Then a '### 7.1 About Us' subsection containing ONLY a clean "
    "2-3 sentence paragraph describing the company and its positioning. "
    "Do NOT include website URLs, email addresses, phone numbers, contact "
    "bullets, or 'Website:' / 'Contact:' lines in this section — keep it a "
    "simple narrative paragraph. Then '### 7.2 Next Steps' with 4-5 bullet "
    "points of the discovery items needed before kickoff, ending with one "
    "short sentence committing to a start window.\n\n"

    "GLOBAL RULES:\n"
    "- Use ASCII punctuation only. NO em-dash (-), en-dash, smart quotes, "
    "or curly apostrophes. Plain '-' and \"...\" only.\n"
    "- Never invent client names, metrics, or systems not present in the "
    "retrieved past-project context.\n"
    "- Tables must use markdown pipe syntax: each row '| cell | cell |' on "
    "its own line, with a '|---|---|' separator after the header.\n"
    "- No meta commentary, AI disclaimers, or approval lines.\n"
    "- No phrases like 'I am excited', 'passionate about', 'cutting-edge', "
    "'leverage synergies', or 'proven track record'.\n"
    "- Paragraphs max 3 sentences. Prefer bullets and tables.\n"
    "- Write in first person plural ('we') as the agency / team voice.\n"
)


# Hard rules re-asserted on every post-approval turn. We re-inject these
# because the original system prompt slips down the recency gradient after
# many turns and the model starts substituting generic letter-template
# behaviour ("Dear [Client Name]", "[Your Name]", "[Email] | [Phone]").
_POST_APPROVAL_HARD_RULES = (
    "HARD RULES (re-asserted):\n"
    "- Return the COMPLETE proposal, not a diff or a change-log.\n"
    "- Preserve the 0-7 numbered section structure from the original "
    "FINAL_PROPOSAL spec. Do NOT collapse it into a cover letter, an email, "
    "or a 'Dear X' greeting.\n"
    "- NEVER write placeholder tokens like '[Client Name]', '[Your Name]', "
    "'[Your Company]', '[Email]', '[Phone]', '[LinkedIn]', '[Contact "
    "Information]'. If a value is genuinely unknown, write "
    "'[to confirm on kickoff call]' instead.\n"
    "- Preserve every GitHub link cited in Section 3 (and elsewhere) "
    "exactly as the previous proposal cited them. Never invent new URLs.\n"
    "- ASCII punctuation only. No em-dash, en-dash, smart quotes, curly "
    "apostrophes.\n"
    "- Voice (I vs we) stays consistent with the previous proposal.\n"
)

REGENERATE_PROPOSAL = (
    "Regenerate the FULL client-ready proposal from scratch. Use the JD "
    "intake, profile, and retrieved past projects in the system prompt as "
    "the only source of truth. The most-recent assistant message in this "
    "window is the previous proposal — use it as a structural reference, "
    "not as text to copy verbatim. If a portfolio attachment block is "
    "present in this user turn, treat those projects as user-attached and "
    "surface each one at least once with its GitHub URL in markdown link "
    "form on first mention.\n\n" + _POST_APPROVAL_HARD_RULES
)

EDIT_PROPOSAL = (
    "Apply the user feedback at the top of this turn to the previous "
    "proposal (the most-recent assistant message in this window). Return "
    "the COMPLETE revised proposal. If a portfolio attachment block is "
    "present in this user turn, keep every listed project cited with its "
    "GitHub URL.\n\n" + _POST_APPROVAL_HARD_RULES
)

QA_INSTRUCTION = (
    "Answer the user's question using only the JD intake, the profile, "
    "and the previous proposal in this window. Be concise (1-3 short "
    "paragraphs). Do NOT regenerate the proposal. Do NOT use placeholder "
    "tokens — if a value is unknown say so plainly."
)


def revise_draft_instruction(feedback: str) -> str:
    """Build the instruction to revise a draft from the user's feedback."""
    return (
        "The user reviewed the draft proposal and asked for changes. Their "
        f"feedback:\n{feedback}\n\n"
        "Revise the SHORT draft proposal accordingly. Keep it brief (about "
        "120-180 words) and finish again with this exact line on its own:\n"
        f"{APPROVAL_PROMPT_LINE}"
    )


def control_turn(user_text: str, instruction: str) -> str:
    """Combine the user's message (if any) with a control instruction."""
    user_text = user_text.strip()
    directive = f"[Instruction to assistant: {instruction}]"
    return f"{user_text}\n\n{directive}" if user_text else directive


def format_rag_context(chunks: list[dict[str, str]], max_snippet: int = 900) -> str:
    """Render retrieved chunks into one block per past project file.

    Excerpts are grouped by their source so the model sees each past project
    as a single coherent item to judge similarity against.
    """
    if not chunks:
        return ""
    by_source: dict[str, list[str]] = {}
    for chunk in chunks:
        source = str(chunk.get("source", "")) or "unknown"
        snippet = " ".join(str(chunk.get("content", "")).split())[:max_snippet]
        if snippet:
            by_source.setdefault(source, []).append(snippet)
    blocks: list[str] = []
    for idx, (source, snippets) in enumerate(by_source.items(), start=1):
        excerpts = "\n   [...]\n".join(snippets)
        blocks.append(f"[{idx}] Past project file: {source}\n{excerpts}")
    return "\n\n".join(blocks)


def _format_company_section(profile: dict | None) -> str:
    """Render the freelancer's own company profile for the system prompt.

    The model uses this as the *voice* of the proposal — name, positioning,
    and any tone cues the user added to their intro. Returns an empty string
    if no profile data is set so prompts stay short for anonymous users.

    If ``intro_verbatim`` is True the full intro is exposed and the model is
    told to use it word-for-word. Otherwise the intro is pre-condensed to
    1-2 sentences on the server *before* the model ever sees it — that way
    the model physically cannot echo back a long About Us paragraph.
    """
    if not profile:
        return ""
    name = str(profile.get("company_name") or "").strip()
    intro = str(profile.get("company_intro") or "").strip()
    signature = str(profile.get("signature") or "").strip()
    verbatim = bool(profile.get("intro_verbatim"))
    if not (name or intro or signature):
        return ""
    lines = ["About the freelancer/agency (write proposals in this voice):"]
    if name:
        lines.append(f"Company name: {name}")
    if intro:
        if verbatim:
            lines.append(
                "Company introduction (USE VERBATIM as the About Us section, "
                "do not paraphrase or shorten):"
            )
            lines.append(intro)
        else:
            short = _condense_intro(intro) or intro
            lines.append(
                "Company positioning (a short, already-condensed line — for "
                "the About Us section keep it to ONE OR TWO sentences using "
                "this positioning. Do not invent longer marketing copy):"
            )
            lines.append(short)
    if signature:
        lines.append(f"Sign off proposals as: {signature}")
    return "\n".join(lines) + "\n\n"


def build_system_prompt(
    intake: JDIntake,
    rag_context: str,
    profile: dict | None = None,
) -> str:
    """Assemble the system prompt from intake data and retrieved context."""
    return (
        f"{_SYSTEM_INSTRUCTIONS}\n\n"
        f"{_format_company_section(profile)}"
        "JD Intake:\n"
        f"Client: {intake.client_name}\n"
        f"Job Title: {intake.job_title}\n"
        f"Budget: {intake.budget}\n"
        f"Timeline: {intake.timeline}\n"
        f"Tech Stack: {intake.tech_stack}\n"
        f"Deliverables: {intake.deliverables}\n"
        f"Constraints: {intake.constraints}\n"
        f"Job Description:\n{intake.job_description}\n\n"
        "Retrieved Similar Past Projects:\n"
        f"{rag_context or 'No matching past project context found.'}\n"
    )
