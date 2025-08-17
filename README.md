
# Voice-Driven LLM Client with Multi-Model Consensus

A comprehensive voice-activated AI assistant that integrates multiple LLMs, tool calling, conversation management, and MCP server capabilities.

## Features

### 🎤 Voice Interface
- **Wake word detection**: Say "Hey GERT" to activate
- **Speech-to-text**: Uses NeMo Parakeet for accurate transcription  
- **Text-to-speech**: Piper TTS for natural voice responses
- **Parallel conversations**: Support for multiple concurrent voice sessions

### 🤖 Multi-LLM Integration  
- **Local Ollama**: Primary LLM with tool calling (Qwen3-30B, GPT-OSS-20B configurable)
- **External APIs**: Gemini 2.5 Pro, GPT-5, Grok, Claude Sonnet
- **Consensus queries**: Get responses from multiple models in parallel
- **Superconsensus**: Advanced cross-model selection system

### 💬 Conversation Management
- **Persistent storage**: All conversations saved with unique IDs
- **Multi-turn support**: Context maintained across conversation turns
- **Auto-summarization**: AI-generated summaries for easy search
- **Conversation search**: Find past conversations by topic/content

### 🛠️ Tool Ecosystem
- **Web search**: DuckDuckGo integration for real-time information
- **Wikipedia**: Direct article lookup and search
- **File operations**: Read/write files in secured directories
- **System tools**: grep, find, head, tail, cat with safety controls
- **Python execution**: Isolated environment for code execution
- **Package management**: Install Python packages in test environment
- **Multi-step workflows**: LLM can make follow-up requests for deeper exploration

### 🔧 Advanced Features
- **MCP Server**: Expose tools to Claude via Model Context Protocol
- **Parallel processing**: Concurrent LLM calls for faster consensus
- **Security controls**: Restricted file access and isolated execution
- **Custom instructions**: Model-specific prompts and behaviors

## Quick Start

### Prerequisites
```bash
# Install dependencies
pip install ollama pyaudio sounddevice numpy ddgs wikipedia anthropic openai google-generativeai nemo-toolkit piper-tts openwakeword

# Ensure Ollama is running with required models
ollama pull qwen3:30b
ollama pull gpt-oss:20b  # Alternative local model
```

### API Keys Setup
Create these files in the `keys/` directory:
- `gemini_api.key` - Google AI Studio API key
- `openai_api.key` - OpenAI API key  
- `grok_api.key` - X.AI Grok API key
- `claude_api.key` - Anthropic Claude API key (optional)

### Voice Models Setup
Download and place in `data/` directory:
- `hey_gert.tflite` - Custom wake word model
- `en_US-kusal-medium.onnx` - Piper TTS voice model

### Basic Usage

**Single conversation mode:**
```bash
python client.py
```

**Parallel conversation mode:**
```bash
python parallel_client.py
```

**Direct API access:**
```python
from llm import run_conversation

# Single query
response, conv_id = run_conversation("What is machine learning?")

# Continue conversation  
response, conv_id = run_conversation("Tell me more about neural networks", conv_id)

# Tool usage
response, conv_id = run_conversation("Search Wikipedia for Python programming")
```

## Multi-Step Workflow Patterns

The system supports intelligent multi-step workflows where the LLM can:

1. **Search then Explore**: Use search tools to get lists of results, then dive deep into specific items
2. **Iterative Tool Execution**: Make informed follow-up tool calls based on previous results within a single turn
3. **Multiple Tool Chains**: Execute multiple tools in sequence during a single conversation turn
4. **Context Building**: Build comprehensive responses by gathering information from multiple sources

### Common Multi-Step Patterns

**Wikipedia Research (Iterative):**
- `wikipedia_search("machine learning")` → Get list of related articles
- *LLM evaluates results and decides to explore specific article*
- `get_wikipedia_page("Deep learning")` → Get full content of specific article

**Web Research (Iterative):**
- `web_search("climate change 2024")` → Get search results with URLs
- *LLM evaluates results and selects most relevant URLs*
- `get_web_page("https://example.com/climate-report")` → Fetch full article content

**File System Exploration:**
- `list_directory("/project/src")` → See available files
- *LLM chooses relevant files to examine*
- `read_file("/project/src/main.py")` → Read specific file content

**Conversation Analysis:**
- `lookup_past_conversations("database optimization")` → Find relevant conversations
- *LLM selects most relevant conversation*
- `load_full_conversation("conv_20240115_123")` → Load complete conversation history

**How It Works:**
The LLM can now see the results of initial tool calls and intelligently decide whether to make follow-up calls for deeper information. This happens automatically within a single conversation turn, with up to 3 iterations to prevent infinite loops.

## Available Tools

### Information & Search
- `wikipedia_search(query)` - Search Wikipedia articles
- `get_wikipedia_page(title)` - Get full content of specific Wikipedia page
- `web_search(query)` - DuckDuckGo web search  
- `get_web_page(url)` - Fetch content of specific web page from search results
- `lookup_past_conversations(query)` - Search conversation history
- `load_full_conversation(conversation_id)` - Load complete message history for specific conversation

### Multi-LLM Access
- `call_gemini(prompt)` - Google Gemini 2.5 Pro
- `call_openai(prompt)` - OpenAI GPT-5  
- `call_grok(prompt)` - X.AI Grok
- `call_claude(prompt)` - Anthropic Claude
- `call_consensus_query(prompt)` - All models in parallel
- `call_superconsensus(prompt)` - Advanced cross-model selection

### File Operations (Secure)
- `read_file(filepath)` - Read files from allowed directories
- `write_file(filepath, content)` - Write files to allowed directories
- `list_directory(dirpath)` - List directory contents

### System Tools (Secure)
- `grep_files(pattern, directory)` - Search file contents
- `find_files(name_pattern, directory)` - Find files by pattern
- `head_file(filepath, lines)` - Show first lines of file
- `cat_file(filepath)` - Display file contents

### Python Execution (Isolated)
- `execute_python_code(code, timeout)` - Run Python in isolated environment
- `install_package(package)` - Install packages in test environment

## MCP Server Integration

The system provides an MCP (Model Context Protocol) server that exposes external tools to Claude Code and Claude Desktop.

### Claude Code CLI Integration

Add the MCP server to Claude Code:

```bash
# Add MCP server to Claude Code
claude mcp add llm-client -- /path/to/llm_client/llm_venv/bin/python /path/to/llm_client/mcp_server.py

# Verify connection
claude mcp list

# Grant permissions (create .claude/settings.json):
{
  "permissions": {
    "allow": [
      "mcp__llm-client__*"
    ]
  }
}
```

**Available MCP Tools:**
- `wikipedia_search` - Search Wikipedia articles
- `web_search` - DuckDuckGo web search  
- `call_grok` - Access X.AI Grok model
- `call_openai` - Access OpenAI GPT-5
- `call_gemini` - Access Google Gemini
- `call_claude` - Access other Claude models
- `call_consensus_query` - Get consensus from multiple LLMs
- `call_superconsensus` - Advanced cross-model selection

### Claude Desktop Integration

For Claude Desktop, add to your Claude config:

```json
{
  "mcpServers": {
    "llm-client": {
      "command": "python",
      "args": ["/path/to/llm_client/mcp_server.py"],
      "description": "Multi-LLM and tool access for Claude"
    }
  }
}
```

## Voice Commands

- **"Hey GERT"** - Activate voice assistant
- **"New conversation"** - Start fresh conversation
- **"Goodbye"/"Stop"** - End current conversation
- **"Shut down"/"Exit program"** - Terminate the application
- **"Search for [topic]"** - Trigger web/Wikipedia search
- **"Get consensus on [question]"** - Multi-LLM consultation
- **"Execute Python: [code]"** - Run Python code
- **"Read file [path]"** - Access file contents

## Keyboard Controls

- **Ctrl+C** - Interrupt/skip current TTS audio playback (conversation continues normally)
  - First Ctrl+C: Stops only the TTS, conversation continues
  - Second Ctrl+C: Exits the entire program

## Configuration

### Audio Settings (`config.py`)
```python
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 280
SILENCE_DURATION = 4.25
MINIMUM_RECORDING_TIME = 4.0
```

### Local Model Selection (`config.py`)
```python
# Choose your preferred local model
DEFAULT_LOCAL_MODEL = "qwen3"  # Options: "qwen3", "gpt-oss"

LOCAL_MODEL_OPTIONS = {
    "gpt-oss": "gpt-oss:20b",
    "qwen3": "qwen3:30b"
}
```

### Custom Instructions (`custom_instructions.md`)
Add your own prompts and behaviors that apply to all LLM calls.

### Security Settings
- File operations restricted to: `/tmp`, `~/Documents`, `~/Desktop`, `~/Downloads`, current directory
- Python execution in isolated temporary environment  
- Network access controlled per tool
- API key access secured in separate files

## Security & Privacy

### API Key Management
- API keys are stored in separate files in the `keys/` directory
- Keys are automatically excluded from git via `.gitignore`
- Never commit API keys to version control

### Data Privacy
- Conversation history stored locally in `conversations/` directory
- Personal voice models and data excluded from git
- No data sent to external services except for LLM API calls

### File System Security
- File operations restricted to approved directories only
- Python code execution isolated in temporary environment
- System commands limited to safe, read-only operations

## Architecture

```
┌─ Voice Interface ─────────────────┐
│  Wake Word → Speech → Text        │
└───────────┬───────────────────────┘
            │
┌─ Core LLM ────────────────────────┐
│  Ollama (gpt-oss:20b)            │
│  + Tool Calling                   │  
└───────────┬───────────────────────┘
            │
┌─ Tool Ecosystem ──────────────────┐
│  ├─ Information (Web, Wikipedia)  │
│  ├─ Multi-LLM (Gemini, GPT, etc) │
│  ├─ File Operations (Secure)      │
│  ├─ System Tools (Secure)         │
│  └─ Python Execution (Isolated)   │
└───────────┬───────────────────────┘
            │
┌─ Storage & Management ────────────┐
│  ├─ Conversation Persistence      │
│  ├─ Auto-summarization           │
│  ├─ Search & Indexing            │
│  └─ MCP Server Interface         │
└───────────────────────────────────┘
```

## Performance Features

- **Parallel LLM calls**: Consensus queries run simultaneously
- **Connection pooling**: Reuses HTTP connections for efficiency  
- **Conversation caching**: Fast access to conversation history
- **Resource management**: Proper cleanup of audio/network resources

## Troubleshooting

**No wake word detection**: Check microphone permissions and wake word model path
**Empty responses**: Verify Ollama is running and gpt-oss:20b model is available
**API errors**: Check API keys are valid and in correct `keys/` directory
**File access denied**: Ensure paths are within allowed directories
**Audio issues**: Check pyaudio/sounddevice installation and audio devices

## License

MIT License - see LICENSE file for details.

## Recent Improvements

### Enhanced Voice Control
- **Conversation Sessions**: Wake word starts a conversation session that continues until ended
- **Conversation Management**: Say "goodbye" or "stop" to end conversations  
- **Program Control**: Say "shut down" to exit the application
- **Wake Word Audio Feedback**: Distinct beep when wake word is detected
- **Streamlined Messages**: Concise system responses ("Goodbye." vs "Goodbye! Say Hey GERT...")
- **Fresh Conversations**: Each wake word activation starts a new conversation context
- **Stable Wake Word Detection**: Model state reset prevents false trigger loops

### Improved Speech Detection
- **Silence Detection Fix**: Fixed critical bug preventing proper silence detection
- **Minimum Recording Time**: Guaranteed 4+ seconds before silence cutoff prevents word truncation
- **Better Volume Analysis**: RMS-based volume calculation for more accurate speech detection
- **Noise Filtering**: Adjustable thresholds to reduce false triggers from background noise
- **Speaker Awareness**: Wake word detection pauses during TTS playback to prevent self-triggering

### Speech Quality Enhancements
- **Markdown Filtering**: Automatic removal of formatting artifacts from TTS
- **Pre-cached Audio**: Common system messages use pre-generated audio for instant playback
- **Better Pronunciation**: Cleaned text processing for more natural speech
- **Empty Command Filtering**: Ignores noise-triggered false commands
- **TTS Interruption**: Press Ctrl+C to skip long audio responses

### Performance Optimizations
- **Parallel Processing**: Multi-LLM consensus queries run simultaneously
- **Enhanced Logging**: Detailed processing flow visibility
- **Faster Responses**: Optimized tool execution and response generation
- **Graceful Shutdown**: Clean audio resource management on exit
- **Qwen3-30B**: High-performance local model with advanced reasoning capabilities

### Audio Configuration
Tunable parameters in `config.py`:
- `SILENCE_THRESHOLD`: Volume level for silence detection (240 = less noise sensitive)
- `SILENCE_DURATION`: How long silence needed before stopping (5.0 seconds)
- `MINIMUM_RECORDING_TIME`: Guaranteed recording time (4.0 seconds)
- `CHUNK_DURATION`: Audio processing chunk size (0.5 seconds)

### Audio Cache Setup
To generate pre-cached audio files for faster system responses:
```bash
python generate_audio_cache.py
```
This creates instant-playback WAV files for common messages in the `audio_cache/` directory.