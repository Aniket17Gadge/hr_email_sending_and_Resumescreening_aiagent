from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from typing import TypedDict, NotRequired, Optional, Dict, List, Sequence, Annotated
import operator



class AgentState(TypedDict):
    # Existing fields
    session_id: str
    message: str
    ai_response: Optional[str]
    classification: Optional[str]
    emails: Optional[List[Dict]]
    email_summary: Optional[str]
    current_agent: Optional[str]
    task_classification: Optional[str]
    email_results: Optional[Dict]
    target_key: Optional[str]
    candidates_found: Optional[int]
    emails_sent: Optional[int]
    
    # Memory-related fields
    messages: Annotated[Sequence[BaseMessage], operator.add]
    thread_id: Optional[str]
    memory_context: Optional[str]  # NEW: Formatted memory context
    conversation_summary: Optional[str]  # NEW: LLM-generated summary
    user_preferences: Optional[Dict]  # NEW: User preferences from history


# class AgentState(TypedDict):
#     # Existing fields
#     session_id: str
#     message: str
#     ai_response: Optional[str]
#     classification: Optional[str]
#     emails: Optional[List[Dict]]
#     email_summary: Optional[str]
#     current_agent: Optional[str]
#     task_classification: Optional[str]
#     email_results: Optional[Dict]
#     target_key: Optional[str]
#     candidates_found: Optional[int]
#     emails_sent: Optional[int]
    
#     # NEW: Memory-related fields
#     messages: Annotated[Sequence[BaseMessage], operator.add]  # For LangGraph memory
#     thread_id: Optional[str]  



# class AgentState(TypedDict):
#     session_id: str
#     message: str
#     ai_response: Optional[str]
#     classification: Optional[str]  # NEW: For message classification
#     emails: Optional[List[Dict]]   # NEW: For storing fetched emails
#     email_summary: Optional[str]   # NEW: For email summary
#     current_agent: Optional[str]
#     task_classification: Optional[str]  # NEW: For storing the current 