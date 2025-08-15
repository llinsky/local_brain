import json
import os
from typing import List, Dict, Any
from datetime import datetime
import ollama

# Create a single, reusable Ollama client instance for summaries
_summary_ollama_client = None

def get_summary_ollama_client():
    """Get or create the shared Ollama client instance for summaries."""
    global _summary_ollama_client
    if _summary_ollama_client is None:
        _summary_ollama_client = ollama.Client()
    return _summary_ollama_client

INDEX_FILE = "conversation_index.json"

def load_index() -> List[Dict[str, Any]]:
    """Load the conversation index from file."""
    if not os.path.exists(INDEX_FILE):
        return []
    
    with open(INDEX_FILE, 'r') as f:
        return json.load(f)

def save_index(index: List[Dict[str, Any]]):
    """Save the conversation index to file."""
    with open(INDEX_FILE, 'w') as f:
        json.dump(index, f, indent=2)

def summarize_conversation(messages: List[Dict[str, Any]]) -> str:
    """Generate a 1-2 sentence summary of a conversation using Ollama."""
    # Extract just the user messages and assistant responses for context
    conversation_text = ""
    for msg in messages:
        if msg['role'] == 'user':
            conversation_text += f"User: {msg['content']}\n"
        elif msg['role'] == 'assistant':
            conversation_text += f"Assistant: {msg['content']}\n"
    
    # Limit conversation text to avoid token limits
    if len(conversation_text) > 2000:
        conversation_text = conversation_text[:2000] + "..."
    
    summary_prompt = f"""Summarize this conversation in 1-2 concise sentences. Focus on the main topic and any key outcomes or decisions.

Conversation:
{conversation_text}

Summary:"""
    
    try:
        client = get_summary_ollama_client()
        response = client.chat(
            model='gpt-oss:20b',
            messages=[{'role': 'user', 'content': summary_prompt}]
        )
        return response['message']['content'].strip()
    except Exception as e:
        return f"Error generating summary: {str(e)}"

def add_conversation_to_index(conversation_id: str, messages: List[Dict[str, Any]]):
    """Add or update a conversation in the index."""
    index = load_index()
    
    # Generate summary
    summary = summarize_conversation(messages)
    
    # Check if conversation already exists in index
    existing_entry = None
    for i, entry in enumerate(index):
        if entry['id'] == conversation_id:
            existing_entry = i
            break
    
    entry = {
        "id": conversation_id,
        "summary": summary,
        "message_count": len(messages),
        "last_updated": datetime.now().isoformat(),
        "filename": f"conversations/{conversation_id}.json"
    }
    
    if existing_entry is not None:
        index[existing_entry] = entry
    else:
        index.append(entry)
    
    save_index(index)

def search_conversations(query: str) -> List[Dict[str, Any]]:
    """Search conversations by summary content."""
    index = load_index()
    query_lower = query.lower()
    
    matching_conversations = []
    for entry in index:
        if query_lower in entry['summary'].lower():
            matching_conversations.append(entry)
    
    # Sort by last updated, most recent first
    matching_conversations.sort(key=lambda x: x['last_updated'], reverse=True)
    
    return matching_conversations

def lookup_past_conversations(query: str) -> str:
    """Tool function to search past conversations."""
    matches = search_conversations(query)
    
    if not matches:
        return json.dumps({"message": "No matching conversations found"})
    
    results = []
    for match in matches[:5]:  # Limit to top 5 results
        results.append({
            "id": match['id'],
            "summary": match['summary'],
            "message_count": match['message_count'],
            "last_updated": match['last_updated']
        })
    
    return json.dumps({"conversations": results})