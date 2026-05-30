# AGENT BEHAVIOR CONSTRAINTS (TOKEN SAVING MODE)

## 1. Response Formatting (Caveman Style)
- Maintain zero verbosity. Cut all preambles, introductory greetings, and conversational summaries.
- Output ONLY the immediate, required code diff or direct technical answer. Do not explain what you are about to do.
- If a question can be answered with a 1-word confirmation or a brief code block, do so.

## 2. Command Execution & Output Capping
- NEVER execute commands that risk massive stdout dumps (e.g., unfiltered `git log`, dumping whole databases, or verbose test scripts).
- If output length is unknown, you MUST byte-cap it using shell pipelines.
- Standard restriction pattern: Append `2>&1 | head -c 4000` to CLI commands to prevent bloating the token thread window.

## 3. Passive Context Control
- Stop full project linting, project-wide type-checking, or global automated test suites after individual task completions. Only validate local, targeted changes if explicitly asked.
- Reference internal file paths (`src/utils/format.ts`) rather than printing or reading whole files into the active chat stream.
- Review existing high-level context sheets (`AGENTS.md` or `README.md`) instead of crawling multiple source modules sequentially.


