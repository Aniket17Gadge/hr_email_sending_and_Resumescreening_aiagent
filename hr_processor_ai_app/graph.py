import asyncio
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from .agentstate import AgentState
from .memory_manager import memory_manager
from .agents import (
    user_msg_analyzer_agent, 
    task_assigner_agent,
    email_fetcher_responder_agent,
    job_applications_emails_summary_agent,
    job_application_screening_agent,
    email_team_agent,
    user_msg_general_agent
)
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import logging

logger = logging.getLogger(__name__)

# Your existing routing functions remain the same
def route_by_classification(state: AgentState) -> str:
    classification = state.get("classification", "")
    if classification == "hr_email_taskupdate":
        return "task_assigner_agent"
    elif classification == "general":
        return "user_msg_general_agent"
    else:
        return END

def route_by_task_classification(state: AgentState) -> str:
    task = state.get("task_classification", "")
    if task == "email_fetcher&responder_agent":
        return "email_fetcher&responder_agent"
    elif task == "job_applications_emails_summary_agent":
        return "job_applications_emails_summary_agent"
    elif task == "job_application_screening_agent":
        return "job_application_screening_agent"
    elif task == "email_team_agent":
        return "email_team_agent"
    else:
        return END

# NEW: Memory-enabled graph builder
async def build_graph_with_memory():
    """Build graph with PostgreSQL memory support"""
    try:
        # Initialize memory
        await memory_manager.initialize()
        memory, conn = await memory_manager.get_memory()
        
        # Create graph
        graph = StateGraph(AgentState)
        
        # Add all nodes (your existing nodes)
        graph.add_node("analyzer", user_msg_analyzer_agent)
        graph.add_node("task_assigner_agent", task_assigner_agent)
        graph.add_node("email_fetcher&responder_agent", email_fetcher_responder_agent)
        graph.add_node("job_applications_emails_summary_agent", job_applications_emails_summary_agent)
        graph.add_node("job_application_screening_agent", job_application_screening_agent)
        graph.add_node("email_team_agent", email_team_agent)
        graph.add_node("user_msg_general_agent", user_msg_general_agent)  # General query agent
        
        # Add routing (your existing routing)
        graph.add_conditional_edges("analyzer", route_by_classification)
        graph.add_conditional_edges("task_assigner_agent", route_by_task_classification)
        
        # Set entry point
        graph.set_entry_point("analyzer")
        
        # Compile with memory checkpointer
        compiled_graph = graph.compile(checkpointer=memory)
        
        logger.info("✅ Graph compiled with PostgreSQL memory")
        return compiled_graph, conn
        
    except Exception as e:
        logger.error(f"❌ Failed to build graph with memory: {e}")
        # Fallback to non-memory graph
        return build_graph(), None

# Keep your existing non-memory graph for fallback
def build_graph():
    """Original graph without memory (fallback)"""
    graph = StateGraph(AgentState)
    
    graph.add_node("analyzer", user_msg_analyzer_agent)
    graph.add_node("task_assigner_agent", task_assigner_agent)
    graph.add_node("email_fetcher&responder_agent", email_fetcher_responder_agent)
    graph.add_node("job_applications_emails_summary_agent", job_applications_emails_summary_agent)
    graph.add_node("job_application_screening_agent", job_application_screening_agent)
    graph.add_node("email_team_agent", email_team_agent)
    
    graph.add_conditional_edges("analyzer", route_by_classification)
    graph.add_conditional_edges("task_assigner_agent", route_by_task_classification)
    
    graph.set_entry_point("analyzer")
    
    return graph.compile()



# # graph.py
# from langgraph.graph import StateGraph, END
# from .agentstate import AgentState
# from .agents import (
#     user_msg_analyzer_agent, 
#     task_assigner_agent,
#     email_fetcher_responder_agent,
#     job_applications_emails_summary_agent,
#     job_application_screening_agent,
#     email_team_agent  # New email team agent
# )

# # Define the conditional router function
# def route_by_classification(state: AgentState) -> str:
#     classification = state.get("classification", "")
#     if classification == "hr_email_taskupdate":
#         return "task_assigner_agent"
#     else:
#         return END  # finish the graph

# # 2. Routing from task assigner by task_classification
# def route_by_task_classification(state: AgentState) -> str:
#     task = state.get("task_classification", "")
#     if task == "email_fetcher&responder_agent":
#         return "email_fetcher&responder_agent"
#     elif task == "job_applications_emails_summary_agent":
#         return "job_applications_emails_summary_agent"
#     elif task == "job_application_screening_agent":
#         return "job_application_screening_agent"
#     elif task == "email_team_agent":  # New routing for email team agent
#         return "email_team_agent"
#     else:
#         return END  # You can add more tasks later

# # Define the LangGraph
# def build_graph():
#     graph = StateGraph(AgentState)

#     # Add all nodes
#     graph.add_node("analyzer", user_msg_analyzer_agent)
#     graph.add_node("task_assigner_agent", task_assigner_agent)
#     graph.add_node("email_fetcher&responder_agent", email_fetcher_responder_agent)
#     graph.add_node("job_applications_emails_summary_agent", job_applications_emails_summary_agent)
#     graph.add_node("job_application_screening_agent", job_application_screening_agent)
#     graph.add_node("email_team_agent", email_team_agent)  # New email team agent node

#     # Conditional routing from analyzer
#     graph.add_conditional_edges("analyzer", route_by_classification)
#     graph.add_conditional_edges("task_assigner_agent", route_by_task_classification)

#     # Set entry and finish points
#     graph.set_entry_point("analyzer")
#     # Remove fixed finish point - let each agent end naturally
    
#     return graph.compile()