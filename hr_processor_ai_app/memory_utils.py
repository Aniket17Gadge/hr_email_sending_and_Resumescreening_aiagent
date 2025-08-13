from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import List, Dict
import json
import os
from dotenv import load_dotenv

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="models/gemini-2.0-flash",
    temperature=0.3,  # Lower temperature for consistent memory processing
    google_api_key=os.getenv("GEMINI_API_KEY")
)

def extract_memory_context(messages: List[BaseMessage], current_message: str) -> Dict:
    """Extract relevant context from conversation history"""
    
    if len(messages) <= 1:
        return {
            "memory_context": "",
            "conversation_summary": "",
            "user_preferences": {}
        }
    
    # Get recent conversation (last 10 messages)
    recent_messages = messages[-10:]
    
    # Format conversation history
    conversation_text = ""
    for msg in recent_messages:
        if isinstance(msg, HumanMessage):
            conversation_text += f"User: {msg.content}\n"
        elif isinstance(msg, AIMessage):
            conversation_text += f"Assistant: {msg.content}\n"
    
    # Generate memory context using LLM
    memory_prompt = f"""
Analyze this conversation history to provide context for the current request.

CONVERSATION HISTORY:
{conversation_text}

CURRENT REQUEST: {current_message}

Extract and return ONLY JSON with these fields:
{{
    "conversation_summary": "Brief summary of what has been discussed",
    "user_preferences": {{"key": "value", "preference_type": "user_preference"}},
    "relevant_context": "Most relevant previous context for current request",
    "session_type": "type of HR session (screening/emailing/general)",
    "previous_actions": ["action1", "action2"]
}}

Focus on:
- HR-related preferences (email tone, screening criteria, etc.)
- Previous tasks completed in this session
- User's communication style
- Relevant decisions made earlier
"""

    try:
        response = llm.invoke([
            SystemMessage(content="Extract conversation context as JSON only."),
            HumanMessage(content=memory_prompt)
        ]).content.strip()
        
        # Clean JSON response
        if response.startswith('```json'):
            response = response.replace('```json', '').replace('```', '').strip()
        elif response.startswith('```'):
            response = response.replace('```', '').strip()
        
        memory_data = json.loads(response)
        
        return {
            "memory_context": memory_data.get("relevant_context", ""),
            "conversation_summary": memory_data.get("conversation_summary", ""),
            "user_preferences": memory_data.get("user_preferences", {}),
            "session_type": memory_data.get("session_type", "general"),
            "previous_actions": memory_data.get("previous_actions", [])
        }
        
    except Exception as e:
        print(f"❌ Error extracting memory context: {e}")
        return {
            "memory_context": f"Previous conversation context available. Current: {current_message}",
            "conversation_summary": "Ongoing HR session",
            "user_preferences": {}
        }
