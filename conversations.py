import json
import os
from datetime import datetime
from typing import List, Dict, Any
from conversation_index import add_conversation_to_index

CONVERSATIONS_DIR = "conversations"

def ensure_conversations_dir():
    if not os.path.exists(CONVERSATIONS_DIR):
        os.makedirs(CONVERSATIONS_DIR)

def save_conversation(conversation_id: str, messages: List[Dict[str, Any]]):
    """Save a conversation to a file."""
    ensure_conversations_dir()
    filepath = os.path.join(CONVERSATIONS_DIR, f"{conversation_id}.json")
    
    conversation_data = {
        "id": conversation_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "messages": messages
    }
    
    with open(filepath, 'w') as f:
        json.dump(conversation_data, f, indent=2)
    
    # Add to index
    add_conversation_to_index(conversation_id, messages)

def load_conversation(conversation_id: str) -> List[Dict[str, Any]]:
    """Load a conversation from file."""
    filepath = os.path.join(CONVERSATIONS_DIR, f"{conversation_id}.json")
    
    if not os.path.exists(filepath):
        return []
    
    with open(filepath, 'r') as f:
        data = json.load(f)
        return data.get("messages", [])

def update_conversation(conversation_id: str, messages: List[Dict[str, Any]]):
    """Update an existing conversation."""
    filepath = os.path.join(CONVERSATIONS_DIR, f"{conversation_id}.json")
    
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        data["messages"] = messages
        data["updated_at"] = datetime.now().isoformat()
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Update index
        add_conversation_to_index(conversation_id, messages)
    else:
        save_conversation(conversation_id, messages)

def generate_conversation_id() -> str:
    """Generate a unique conversation ID based on timestamp."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def clear_conversation_history() -> str:
    """Clear all conversation history and index."""
    import shutil
    import json
    
    try:
        # Remove conversations directory
        if os.path.exists(CONVERSATIONS_DIR):
            shutil.rmtree(CONVERSATIONS_DIR)
            
        # Clear conversation index
        index_file = "conversation_index.json"
        if os.path.exists(index_file):
            os.remove(index_file)
            
        return json.dumps({"success": True, "message": "All conversation history cleared"})
    except Exception as e:
        return json.dumps({"error": f"Error clearing history: {str(e)}"})

def delete_conversation(conversation_id: str) -> str:
    """Delete a specific conversation."""
    try:
        # Remove conversation file
        filepath = os.path.join(CONVERSATIONS_DIR, f"{conversation_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            
            # Update index by removing this conversation
            from conversation_index import load_index, save_index
            index = load_index()
            index = [entry for entry in index if entry["id"] != conversation_id]
            save_index(index)
            
            return json.dumps({"success": True, "conversation_id": conversation_id, "action": "deleted"})
        else:
            return json.dumps({"error": f"Conversation {conversation_id} not found"})
            
    except Exception as e:
        return json.dumps({"error": f"Error deleting conversation: {str(e)}"})

def list_conversations() -> str:
    """List all stored conversations."""
    try:
        from conversation_index import load_index
        index = load_index()
        
        conversations = []
        for entry in index:
            conversations.append({
                "id": entry["id"],
                "summary": entry["summary"],
                "message_count": entry["message_count"],
                "last_updated": entry["last_updated"]
            })
            
        return json.dumps({"conversations": conversations, "total": len(conversations)})
    except Exception as e:
        return json.dumps({"error": f"Error listing conversations: {str(e)}"})