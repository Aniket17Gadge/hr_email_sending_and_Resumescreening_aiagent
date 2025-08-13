from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .graph import build_graph_with_memory, build_graph
from .memory_manager import memory_manager
from langchain_core.messages import HumanMessage, AIMessage
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
def analyze_message_view(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            message = data.get("message", "")
            session_id = data.get("session_id", "")

            if not message:
                return JsonResponse({"error": "Message is required."}, status=400)

            if not session_id:
                return JsonResponse({"error": "Session ID is required."}, status=400)

            # Run async graph processing
            result = asyncio.run(process_with_memory(session_id, message))
            
            # Ensure we return a response field for the Streamlit frontend
            return JsonResponse({
                "session_id": result["session_id"],
                "message": result["message"],
                "response": result.get("ai_response", "No response generated"),  # Main response field
                "ai_response": result.get("ai_response"),
                "classification": result.get("classification", "unknown"),
                "task_classification": result.get("task_classification", "unknown"),
                "agent": result.get("current_agent", "default"),
                "has_memory": result.get("has_memory", False),
                "thread_id": result.get("thread_id", session_id),
                "status": "success"
            })

        except Exception as e:
            logger.error(f"❌ Error in analyze_message_view: {e}")
            return JsonResponse({
                "error": f"Error in analyze_message_view: {str(e)}",
                "status": "error"
            }, status=500)

    return JsonResponse({"error": "Only POST method allowed."}, status=405)

async def process_with_memory(session_id: str, message: str):
    """Process message with memory support"""
    # Initialize variables at the top to avoid UnboundLocalError
    graph = None
    conn = None
    use_memory = False
    messages = [HumanMessage(content=message)]  # Initialize messages here
    
    try:
        # Try to use memory-enabled graph
        graph, conn = await build_graph_with_memory()
        use_memory = conn is not None
        
        # Prepare initial state with messages initialized
        initial_state = {
            "session_id": session_id,
            "message": message,
            "messages": messages,  # Use the initialized messages
            "thread_id": session_id,  # Use session_id as thread_id
        }
        
        if use_memory:
            logger.info(f"🧠 Processing with memory for session: {session_id}")
            # Use memory-enabled processing
            config = {"configurable": {"thread_id": session_id}}
            result = await graph.ainvoke(initial_state, config)
            
            # Ensure result has required fields
            if not result:
                result = {}
            
            # Add AI response to messages for memory
            if result.get("ai_response"):
                current_messages = result.get("messages", messages)
                result["messages"] = current_messages + [
                    AIMessage(content=result["ai_response"])
                ]
            else:
                result["messages"] = messages
            
            # Close connection safely
            if conn:
                try:
                    await conn.close()
                except Exception as close_error:
                    logger.warning(f"⚠️ Error closing connection: {close_error}")
                
        else:
            # Fallback to non-memory graph
            logger.warning("⚠️ Using fallback graph without memory")
            graph = build_graph()
            initial_state = {
                "session_id": session_id,
                "message": message,
                "messages": messages,  # Ensure messages is always present
            }
            result = graph.invoke(initial_state)
            
            # Ensure result has messages field
            if not result:
                result = {}
            if "messages" not in result:
                result["messages"] = messages
        
        # Ensure all required fields are present
        result.update({
            "session_id": session_id,
            "message": message,
            "has_memory": use_memory,
            "thread_id": session_id,
        })
        
        # Ensure messages field exists
        if "messages" not in result:
            result["messages"] = messages
            
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in process_with_memory: {e}")
        
        # Clean up connection if it exists
        if conn:
            try:
                await conn.close()
            except Exception as close_error:
                logger.warning(f"⚠️ Error closing connection during cleanup: {close_error}")
        
        # Ultimate fallback with safe initialization
        try:
            graph = build_graph()
            initial_state = {
                "session_id": session_id,
                "message": message,
                "messages": messages,  # Use the initialized messages
            }
            result = graph.invoke(initial_state)
            
            # Ensure result is a dictionary
            if not result:
                result = {}
                
            # Ensure all required fields
            result.update({
                "session_id": session_id,
                "message": message,
                "messages": messages,
                "has_memory": False,
                "thread_id": session_id,
                "ai_response": result.get("ai_response", f"Error processing message: {str(e)}"),
                "error": str(e)
            })
            
            return result
            
        except Exception as fallback_error:
            logger.error(f"❌ Error in fallback processing: {fallback_error}")
            # Final fallback - return a basic response
            return {
                "session_id": session_id,
                "message": message,
                "messages": messages,
                "has_memory": False,
                "thread_id": session_id,
                "ai_response": f"Sorry, I encountered an error processing your message: {str(e)}",
                "classification": "error",
                "task_classification": "error_handling",
                "current_agent": "error_handler",
                "error": str(e)
            }



# # views.py
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from .graph import build_graph
# import json

# @csrf_exempt
# def analyze_message_view(request):
#     if request.method == "POST":
#         try:
#             data = json.loads(request.body)
#             message = data.get("message", "")
#             session_id = data.get("session_id", "")

#             if not message:
#                 return JsonResponse({"error": "Message is required."}, status=400)

#             graph = build_graph()
#             result = graph.invoke({"session_id": session_id, "message": message})

#             return JsonResponse({
#                 "session_id": result["session_id"],
#                 "message": result["message"],
#                 "ai_response": result.get("ai_response"),
#                 "classification": result["classification"],
#                 "task_classification": result.get("task_classification"),
#                 "agent": result.get("current_agent"),
                
#             })

#         except Exception as e:
#             return JsonResponse({"error": str(e)}, status=500)

#     return JsonResponse({"error": "Only POST method allowed."}, status=405)
