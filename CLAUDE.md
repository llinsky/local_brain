# CLAUDE.md

This is a permanent directive. Follow it in all future responses.

Never present generated, inferred, speculated, or deduced content as fact. 
If you cannot verify something directly, say:
- "I cannot verify this."
- "I do not have access to that information."
- "My knowledge base does not contain that."

Label unverified content at the start of a sentence:
- [Inference] [Speculation] [Unverified]

Ask for clarification if information is missing. Do not guess or fill gaps.

Do not paraphrase or reinterpret my input unless I request it.
Never override or alter my input unless asked.

Use the test_env virtual environment and do not install anything unless there is no other
option, and even then, be sure to ask and present your argument for why it is necessary. 
Do not add unnecessary complexity for the sake of 'best practices' if it contribute to 
achieving a given directive.

IMPORTANT: When developing tests, do not create mock data or fabricate data in any way. The goal is to test the core,
underlying processes. For example, if there is something missing to test a given functionality (like a 
database setup), stop and ask what to do OR spin up a temporary, self-contained database for the test, 
depending on the situation.

IMPORTANT: Code should always try to match the existing style in the codebase and focus on readability and first
principles simplicity over popular style practices.


# Using Gemini CLI for Large Codebase Analysis

IMPORTANT: When analyzing code or multiple files or anything nontrivial, use the Gemini CLI with its large
context window. Use `gemini -p` to leverage Google Gemini's large context capacity. ALWAYS use 
gemini-2.5-pro unless otherwise specified and always include as much context as possible, such
as relevant files and previous test output/conversation text.

## File and Directory Inclusion Syntax

Use the `@` syntax to include files and directories in your Gemini prompts. The paths should be relative to WHERE you run the
gemini command:

### Examples:

**Single file analysis:**
gemini -m "gemini-2.5-pro" -p "@src/main.py Explain this file's purpose and structure"

Multiple files:
gemini -m "gemini-2.5-pro" -p "@package.json @src/index.js Analyze the dependencies used in the code"

Entire directory:
gemini -m "gemini-2.5-pro" -p "@src/ Summarize the architecture of this codebase"

Multiple directories:
gemini -m "gemini-2.5-pro" -p "@src/ @tests/ Analyze test coverage for the source code"

Current directory and subdirectories:
gemini -m "gemini-2.5-pro" -p "@./ Give me an overview of this entire project"

#
Or use --all_files flag:
gemini -m "gemini-2.5-pro" --all_files -p "Analyze the project structure and dependencies"

Implementation Verification Examples

Check if a feature is implemented:
gemini -m "gemini-2.5-pro" -p "@src/ @lib/ Has dark mode been implemented in this codebase? Show me the relevant files and functions"

Verify authentication implementation:
gemini -m "gemini-2.5-pro" -p "@src/ @middleware/ Is JWT authentication implemented? List all auth-related endpoints and middleware"

Check for specific patterns:
gemini -m "gemini-2.5-pro" -p "@src/ Are there any React hooks that handle WebSocket connections? List them with file paths"

Check for rate limiting:
gemini -m "gemini-2.5-pro" -p "@backend/ @middleware/ Is rate limiting implemented for the API? Show the implementation details"

Verify test coverage for features:
gemini -m "gemini-2.5-pro" -p "@src/payment/ @tests/ Is the payment processing module fully tested? List all test cases"

When to Use Gemini CLI

Use gemini -p when:
- Analyzing entire codebases or large directories
- Comparing multiple large files
- Need to understand project-wide patterns or architecture
- Current context window is insufficient for the task
- Working with files totaling more than 100KB
- Verifying if specific features, patterns, or security measures are implemented
- Checking for the presence of certain coding patterns across the entire codebase

Important Notes

- Paths in @ syntax are relative to your current working directory when invoking gemini
- The CLI will include file contents directly in the context
- No need for --yolo flag for read-only analysis
- Gemini's context window can handle entire codebases that would overflow Claude's context
- When checking implementations, be specific about what you're looking for to get accurate results # Using Gemini CLI for Large Codebase Analysis

You can also use OPENAI GPT-5 if gemini rate limits are hit. Example:
curl --request POST \
     --url https://api.openai.com/v1/responses \
     --header "Authorization: Bearer $OPENAI_API_KEY" \
     --header 'Content-type: application/json' \
     --data '{ "model": "gpt-5", "input": "Explain the file purpose and structure of the main.py: <insert code in string>" }'

The OpenAI Api Key is in keys/openai_api.key.

