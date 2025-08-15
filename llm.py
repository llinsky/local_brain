import json
import ollama
import time
import wikipedia
from ddgs import DDGS
from openai import OpenAI
import google.generativeai as genai
from timeout import Timeout
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import logging
from conversations import save_conversation, load_conversation, update_conversation, generate_conversation_id, clear_conversation_history, delete_conversation, list_conversations
from conversation_index import lookup_past_conversations
from llm_instructions import get_full_prompt
from file_tools import read_file, write_file, append_file, delete_file, list_directory, create_directory
from system_tools import grep_files, find_files, head_file, tail_file, cat_file, wc_file
from python_executor import execute_python_code, install_package, list_installed_packages

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create a single, reusable Ollama client instance
_ollama_client = None

def get_ollama_client():
    """Get or create the shared Ollama client instance."""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = ollama.Client()
    return _ollama_client

def notify_human(message: str = "User input required"):
    """Play a notification sound and speak a message when user input is needed."""
    try:
        from speech import play_notification_beep, speak_or_cached, speak
        import os
        
        # Play a distinctive notification sound (higher pitch, longer duration)
        play_notification_beep(1200, 0.3)
        
        # Speak the notification message using cached audio if available
        cache_filename = "user_input_required.wav" if message == "User input required" else None
        if cache_filename and os.path.exists(os.path.join("audio_cache", cache_filename)):
            speak_or_cached(message, cache_filename)
        else:
            speak(message)
            
        logger.info(f"Human notification played: {message}")
        
    except Exception as e:
        # Fallback: at least log the message if audio fails
        logger.warning(f"Could not play audio notification '{message}': {e}")
        print(f"🔔 NOTIFICATION: {message}")  # Console fallback

# Define tools (functions)
def wikipedia_search(query: str):
    """Searches Wikipedia for a query. Returns the summary of the exact matching page if it exists, otherwise a list of the top 5 search results."""
    try:
        page = wikipedia.page(query)
        return json.dumps({"exact_match": True, "summary": page.summary})
    except wikipedia.exceptions.PageError:
        results = wikipedia.search(query, results=5)
        return json.dumps({"exact_match": False, "results": results})
    except Exception as e:
        return json.dumps({"error": str(e)})

def web_search(query: str):
    """Performs a web search for the given query and returns the top 5 results."""
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=5)]
        return json.dumps(results)
    except Exception as e:
        return json.dumps({"error": str(e)})

def call_grok(prompt: str):
    """Calls the Grok API with the given prompt and returns the response."""
    try:
        with open("keys/grok_api.key", "r") as fp:
            key = fp.readlines()[0].strip()
        client = OpenAI(
            api_key=key,
            base_url="https://api.x.ai/v1"
        )
        
        system_prompt = get_full_prompt("grok")
        response = client.chat.completions.create(
            model="grok-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        return json.dumps({"response": response.choices[0].message.content})
    except Exception as e:
        return json.dumps({"error": str(e)})

def call_openai(prompt: str):
    """Calls the OpenAI API with the given prompt and returns the response."""
    try:
        with open("keys/openai_api.key", "r") as fp:
            key = fp.readlines()[0].strip()
        client = OpenAI(api_key=key)
        
        system_prompt = get_full_prompt("openai")
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        return json.dumps({"response": response.choices[0].message.content})
    except Exception as e:
        return json.dumps({"error": str(e)})

def call_gemini(prompt: str):
    """Calls the Gemini API with the given prompt and returns the response."""
    try:
        with open("keys/gemini_api.key", "r") as fp:
            key = fp.readlines()[0].strip()
        genai.configure(api_key=key)
        
        system_prompt = get_full_prompt("gemini")
        full_prompt = f"{system_prompt}\n\nUser: {prompt}"
        
        model = genai.GenerativeModel('gemini-2.5-pro')
        response = model.generate_content(full_prompt)
        return json.dumps({"response": response.text})
    except Exception as e:
        return json.dumps({"error": str(e)})

def call_claude(prompt: str):
    """Calls the Claude API with the given prompt and returns the response."""
    try:
        import anthropic
        
        with open("keys/claude_api.key", "r") as fp:
            key = fp.readlines()[0].strip()
        
        client = anthropic.Anthropic(api_key=key)
        system_prompt = get_full_prompt("claude")
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return json.dumps({"response": response.content[0].text})
    except Exception as e:
        return json.dumps({"error": str(e)})

def call_consensus_query(prompt: str):
    """Calls Gemini, Grok, GPT-5, and Claude in parallel and returns the response."""
    
    # Define the functions to call in parallel
    model_functions = {
        'gemini': lambda: call_gemini(prompt),
        'grok': lambda: call_grok(prompt), 
        'gpt': lambda: call_openai(prompt),
        'claude': lambda: call_claude(prompt)
    }
    
    responses = {}
    
    # Execute all model calls in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Submit all tasks
        future_to_model = {executor.submit(func): model for model, func in model_functions.items()}
        
        # Collect results as they complete
        for future in as_completed(future_to_model):
            model = future_to_model[future]
            try:
                result = future.result(timeout=600)  # 10 minute timeout per model
                responses[model] = result
            except Exception as e:
                responses[model] = json.dumps({"error": f"Error calling {model}: {str(e)}"})

    formatted_responses = f"""
    Responses for prompt: {prompt}
    
    Gemini response: {responses.get('gemini', 'No response')}
    
    Grok response: {responses.get('grok', 'No response')}
    
    GPT-5 response: {responses.get('gpt', 'No response')}
    
    Claude response: {responses.get('claude', 'No response')}
    
    """
    with open(f"/tmp/call_consensus_query_response_{int(time.time())}.txt", "w") as fp:
        fp.write(formatted_responses)
    return formatted_responses

def call_superconsensus(prompt: str):
    """Calls 2 of each model in parallel and uses a different model to choose the best responses."""
    
    # Define all model calls to execute in parallel
    model_calls = {
        'gemini_1': lambda: call_gemini(prompt),
        'gemini_2': lambda: call_gemini(prompt),
        'gpt_1': lambda: call_openai(prompt),
        'gpt_2': lambda: call_openai(prompt),
        'grok_1': lambda: call_grok(prompt),
        'grok_2': lambda: call_grok(prompt),
        'claude_1': lambda: call_claude(prompt),
        'claude_2': lambda: call_claude(prompt)
    }
    
    responses = {}
    
    # Execute all model calls in parallel
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_call = {executor.submit(func): call_name for call_name, func in model_calls.items()}
        
        for future in as_completed(future_to_call):
            call_name = future_to_call[future]
            time.sleep(0.5)
            try:
                result = future.result(timeout=600)
                responses[call_name] = result
            except Exception as e:
                responses[call_name] = json.dumps({"error": f"Error in {call_name}: {str(e)}"})
    
    # Extract individual responses
    gemini_1 = responses.get('gemini_1', 'No response')
    gemini_2 = responses.get('gemini_2', 'No response')
    gpt_1 = responses.get('gpt_1', 'No response')
    gpt_2 = responses.get('gpt_2', 'No response')
    grok_1 = responses.get('grok_1', 'No response')
    grok_2 = responses.get('grok_2', 'No response')
    claude_1 = responses.get('claude_1', 'No response')
    claude_2 = responses.get('claude_2', 'No response')


    # Execute response selection in parallel
    def select_best_gemini():
        gemini_selector_prompt = f"""
        The following are 2 responses for this prompt: <start_prompt>{prompt}</start_prompt>
        
        Response A: <response>{gemini_1}</response>
        Response B: <response>{gemini_2}</response>
        
        Choose A or B and briefly explain why. Then provide your own opinion on the topic.
        """
        return call_openai(gemini_selector_prompt)
    
    def select_best_grok():
        grok_selector_prompt = f"""
        The following are 2 responses for this prompt: <start_prompt>{prompt}</start_prompt>
        
        Response A: <response>{grok_1}</response>
        Response B: <response>{grok_2}</response>
        
        Choose A or B and briefly explain why. Then provide your own opinion on the topic.
        """
        return call_gemini(grok_selector_prompt)
    
    def select_best_gpt():
        gpt_selector_prompt = f"""
        The following are 2 responses for this prompt: <start_prompt>{prompt}</start_prompt>
        
        Response A: <response>{gpt_1}</response>
        Response B: <response>{gpt_2}</response>
        
        Choose A or B and briefly explain why. Then provide your own opinion on the topic.
        """
        return call_grok(gpt_selector_prompt)
    
    def select_best_claude():
        claude_selector_prompt = f"""
        Choose the better response for this prompt: {prompt}
        
        Response A: {claude_1}
        Response B: {claude_2}
        
        Choose A or B and briefly explain why. Then provide your own opinion on the topic.
        """
        return call_gemini(claude_selector_prompt)
    
    # Run all selections in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            'best_gemini': executor.submit(select_best_gemini),
            'best_grok': executor.submit(select_best_grok),
            'best_gpt': executor.submit(select_best_gpt),
            'best_claude': executor.submit(select_best_claude)
        }
        
        selection_results = {}
        for name, future in futures.items():
            try:
                selection_results[name] = future.result(timeout=600)  # 10 minute timeout
            except Exception as e:
                logger.error(f"Error in {name}: {e}")
                selection_results[name] = "Selection failed"
    
    best_gemini = selection_results.get('best_gemini', 'Selection failed')
    best_grok = selection_results.get('best_grok', 'Selection failed')
    best_gpt = selection_results.get('best_gpt', 'Selection failed')
    best_claude = selection_results.get('best_claude', 'Selection failed')
    
    superconsensus_result = f"""
    SUPERCONSENSUS for prompt: {prompt}
    
    Best Gemini (selected by GPT-5): {best_gemini}
    
    Best Grok (selected by Gemini): {best_grok}
    
    Best GPT-5 (selected by Grok): {best_gpt}
    
    Best Claude (selected by Claude): {best_claude}
    """
    
    with open(f"/tmp/superconsensus_response_{int(time.time())}.txt", "w") as fp:
        fp.write(superconsensus_result)
    
    return superconsensus_result


# Define the tool specifications for the model
tools = [
    {
        "type": "function",
        "function": {
            "name": "wikipedia_search",
            "description": "Searches Wikipedia for a query. Returns the summary of the exact matching page if it exists, otherwise a list of the top 5 search results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query for Wikipedia",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Performs a web search for the given query and returns the top 5 results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The web search query",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "call_grok",
            "description": "Calls the Grok API with a prompt and returns the response.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt to send to Grok",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "call_openai",
            "description": "Calls the OpenAI API with a prompt and returns the response.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt to send to OpenAI",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "call_gemini",
            "description": "Calls the Gemini API with a prompt and returns the response.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt to send to Gemini",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "call_claude",
            "description": "Calls the Claude API with a prompt and returns the response.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt to send to Claude",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "call_consensus_query",
            "description": "Calls multiple LLM's (Gemini, GPT-5, Grok, Claude) to get a consensus.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt to send to the models.",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "call_superconsensus", 
            "description": "Calls 2 instances of each model and uses cross-model selection to pick the best responses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt to send to all models for superconsensus.",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_past_conversations",
            "description": "Search past conversations by topic or content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to find relevant past conversations.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    # File operations tools
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a file from an allowed directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the file to read"},
                },
                "required": ["filepath"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file in an allowed directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the file to write"},
                    "content": {"type": "string", "description": "Content to write to the file"},
                },
                "required": ["filepath", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List contents of a directory in an allowed location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dirpath": {"type": "string", "description": "Path to the directory to list"},
                },
                "required": ["dirpath"],
            },
        },
    },
    # System tools
    {
        "type": "function",
        "function": {
            "name": "grep_files",
            "description": "Search for patterns in files using grep.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Pattern to search for"},
                    "directory": {"type": "string", "description": "Directory to search in (optional)"},
                    "recursive": {"type": "boolean", "description": "Search recursively (optional)"},
                    "case_insensitive": {"type": "boolean", "description": "Case insensitive search (optional)"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Find files using patterns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name_pattern": {"type": "string", "description": "File name pattern (optional)"},
                    "directory": {"type": "string", "description": "Directory to search in (optional)"},
                    "file_type": {"type": "string", "description": "Type: 'file' or 'directory' (optional)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "head_file",
            "description": "Show first N lines of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the file"},
                    "lines": {"type": "integer", "description": "Number of lines to show (default 10)"},
                },
                "required": ["filepath"],
            },
        },
    },
    # Python execution tools
    {
        "type": "function",
        "function": {
            "name": "execute_python_code",
            "description": "Execute Python code in an isolated environment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)"},
                },
                "required": ["code"],
            },
        },
    },
    # Conversation management tools
    {
        "type": "function",
        "function": {
            "name": "clear_conversation_history",
            "description": "Clear all conversation history and index.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "delete_conversation",
    #         "description": "Delete a specific conversation by ID.",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "conversation_id": {"type": "string", "description": "ID of conversation to delete"},
    #             },
    #             "required": ["conversation_id"],
    #         },
    #     },
    # },
    {
        "type": "function",
        "function": {
            "name": "list_conversations",
            "description": "List all stored conversations with summaries.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

# 4. Interact with the model
def run_conversation(prompt: str, conversation_id: str = None):
    logger.info(f"Starting conversation - ID: {conversation_id}, Prompt: {prompt[:100]}...")
    
    # Load existing conversation or start new one
    if conversation_id:
        messages = load_conversation(conversation_id)
        if not messages:
            messages = []
        logger.info(f"Loaded existing conversation with {len(messages)} messages")
    else:
        conversation_id = generate_conversation_id()
        messages = []
        logger.info(f"Created new conversation with ID: {conversation_id}")
    
    # Add system prompt if this is a new conversation
    if not messages:
        system_prompt = get_full_prompt("ollama")
        messages.append({'role': 'system', 'content': system_prompt})
    
    # Add the new user message
    messages.append({'role': 'user', 'content': prompt})

    # First interaction with the model
    logger.info("Sending request to Ollama LLM...")
    client = get_ollama_client()
    response = client.chat(
        model='gpt-oss:20b',  # Or another model that supports function calling
        messages=messages,
        tools=tools,
    )
    logger.info("Received response from Ollama LLM")

    # Convert Ollama message to JSON-serializable format
    message_dict = {
        'role': response.message.role,
        'content': response.message.content
    }
    if hasattr(response.message, 'tool_calls') and response.message.tool_calls:
        # Convert tool calls to serializable format
        tool_calls = []
        for tc in response.message.tool_calls:
            tool_call_dict = {
                'function': {
                    'name': tc.function.name,
                    'arguments': tc.function.arguments
                }
            }
            tool_calls.append(tool_call_dict)
        message_dict['tool_calls'] = tool_calls
    
    messages.append(message_dict)

    # Check if the model wants to call a tool
    if hasattr(response.message, 'tool_calls') and response.message.tool_calls:
        tool_call = response.message.tool_calls[0]
        function_name = tool_call.function.name
        function_args = tool_call.function.arguments
        
        logger.info(f"Executing tool: {function_name} with args: {function_args}")

        # 5. Execute the tool
        if function_name == "wikipedia_search":
            with Timeout(30):
                result = wikipedia_search(**function_args)
        elif function_name == "web_search":
            with Timeout(30):
                result = web_search(**function_args)
        elif function_name == "call_grok":
            with Timeout(600):
                result = call_grok(**function_args)
        elif function_name == "call_openai":
            with Timeout(600):
                result = call_openai(**function_args)
        elif function_name == "call_gemini":
            with Timeout(600):
                result = call_gemini(**function_args)
        elif function_name == "call_claude":
            with Timeout(600):
                result = call_claude(**function_args)
        elif function_name == "call_consensus_query":
            with Timeout(900):
                result = call_consensus_query(**function_args)
        elif function_name == "call_superconsensus":
            with Timeout(1800):  # 30 minutes for superconsensus
                result = call_superconsensus(**function_args)
        elif function_name == "lookup_past_conversations":
            with Timeout(30):
                result = lookup_past_conversations(**function_args)
        # File operations
        elif function_name == "read_file":
            with Timeout(30):
                result = read_file(**function_args)
        elif function_name == "write_file":
            with Timeout(30):
                result = write_file(**function_args)
        elif function_name == "list_directory":
            with Timeout(30):
                result = list_directory(**function_args)
        # System tools
        elif function_name == "grep_files":
            with Timeout(60):
                result = grep_files(**function_args)
        elif function_name == "find_files":
            with Timeout(60):
                result = find_files(**function_args)
        elif function_name == "head_file":
            with Timeout(30):
                result = head_file(**function_args)
        # Python execution
        elif function_name == "execute_python_code":
            with Timeout(60):
                result = execute_python_code(**function_args)
        # Conversation management
        elif function_name == "clear_conversation_history":
            with Timeout(30):
                result = clear_conversation_history()
        elif function_name == "list_conversations":
            with Timeout(30):
                result = list_conversations()
        else:
            result = "Unknown function"

        # 6. Return the result to the model using a simple approach that works
        # Create a follow-up prompt that includes the tool result
        followup_prompt = f"Based on the {function_name} result: {result}\n\nPlease provide a helpful response to the user's original question."
        
        # Add the tool execution info to conversation history
        messages.append({
            'role': 'assistant',
            'content': f"I'll search for that information using {function_name}.",
            'tool_calls': [{
                'function': {
                    'name': function_name,
                    'arguments': function_args
                }
            }]
        })
        
        messages.append({
            'role': 'tool',
            'content': result
        })
        
        # Make a simple call with the follow-up prompt
        logger.info("Generating final response based on tool result...")
        final_response = client.chat(
            model='gpt-oss:20b', 
            messages=[
                {'role': 'system', 'content': get_full_prompt("ollama")},
                {'role': 'user', 'content': followup_prompt}
            ]
        )
        logger.info("Final response generated")
        
        print(final_response.message.content)
        
        # Add final response to conversation history
        final_message_dict = {
            'role': 'assistant',
            'content': final_response.message.content
        }
        messages.append(final_message_dict)
        
        # Save the updated conversation
        update_conversation(conversation_id, messages)
        
        return final_response.message.content, conversation_id
    else:
        print(response.message.content)
        
        # Save the conversation
        update_conversation(conversation_id, messages)
        
        return response.message.content, conversation_id
