---
description: Review notes in a chosen topic folder and simplify Back content to 3-7 words.
---

You are helping me optimize topic-based notes.

Context:
- Folder to review: notes/<topic-folder>
- Each markdown file is one note.
- Front is the question.
- Back is the answer.

Goal:
- Make Back content as simple as possible.
- Target length for each Back: 3 to 7 words.

Tasks:
1. Read all markdown files in notes/<topic-folder>.
2. For each file, extract the Back section and count words.
3. List every file that does NOT meet the 3-7 word Back rule.
4. For each non-compliant file, propose a replacement Back line that is:
   - 3 to 7 words
  - Conceptually accurate for the note topic
   - Easy to memorize
5. Use internet sources to validate concepts and wording quality.
6. Include source links used for validation.

Output format:
- First, summary:
  - total files reviewed
  - number compliant
  - number non-compliant
- Then a table with columns:
  - File
  - Current Back word count
  - Suggested Back (3-7 words)
  - Rationale (one short sentence)
- Then a short source list of URLs used.

Quality rules:
- Prefer precise domain terminology over vague wording.
- Keep one idea per Back line.
- Avoid long clauses, punctuation-heavy text, and formulas unless essential.
- Keep style consistent across notes.

Optional follow-up mode:
- If I say "apply updates", edit the markdown files with the suggested Back lines and prepare them for note update-from-file workflow.
