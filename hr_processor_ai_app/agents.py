from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from .agentstate import AgentState
import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv
from typing import TypedDict, NotRequired
from django.utils import timezone
from langchain_google_genai import ChatGoogleGenerativeAI
import logging
from .utils import email_fetcher,screen_and_summarize_applications
from .memory_utils import extract_memory_context

import logging

logger = logging.getLogger(__name__)

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

llm = ChatGoogleGenerativeAI(
    model="models/gemini-2.0-flash",
    temperature=0.7,
    google_api_key=GEMINI_API_KEY
)

def user_msg_general_agent(state: AgentState) -> AgentState:
    """Agent: answer to general query"""
    message = state["message"]
    try:
       
        history_messages = state.get("messages", [])

        memory_data = extract_memory_context(history_messages, message)

        messages = [
            SystemMessage(
                content=f"""You are a general-purpose AI assistant.

CONVERSATION CONTEXT:
{memory_data['conversation_summary']}

USER PREFERENCES:
{json.dumps(memory_data['user_preferences'], indent=2)}

PREVIOUS ACTIONS IN THIS SESSION:
{', '.join(memory_data['previous_actions'])}

Current task: Your task is to understand and directly answer any user query to the best of your ability. Use clear, accurate, and concise language. You can handle questions across a wide range of topics, including but not limited to:

- Factual knowledge
- How-to instructions
- Explanations and summaries
- Recommendations
- Technical or creative tasks

Always provide a helpful and complete response. Do not avoid the question unless it violates safety guidelines. Use reasoning when necessary, and keep the user’s intent in mind.

Message: "{message}"

Respond with a clear and complete answer to the query above.
"""
            ),
            HumanMessage(content=message),
        ]

        llm_response = llm.invoke(messages)
        response = llm_response.content.strip()

        print(f"Analyzer Agent Response: {response}")

        return {
            **state,
            "ai_response": response,
            "current_agent": "user_msg_general_agent"
        }

    except Exception as e:
        logger.error(f"❌ Error in user_msg_general_agent: {e}")
        return {
            **state,
            "ai_response": "I'm sorry, something went wrong while processing your query.",
            "current_agent": "user_msg_general_agent"
        }




def user_msg_analyzer_agent(state: AgentState) -> AgentState:
    """Agent 1: Analyzes if input is email or general query"""
    message = state["message"]
    history_messages = state.get("messages", [])

    memory_data = extract_memory_context(history_messages, message)


    messages = [
        SystemMessage(
            content=f"""You are a classification agent.
            CONVERSATION CONTEXT:
{memory_data['conversation_summary']}

USER PREFERENCES:
{json.dumps(memory_data['user_preferences'], indent=2)}



Current task:

Your task is to analyze the following message and classify it into one of the following categories:

- **hr_email_taskupdate** – if the message relates to HR tasks or email-related actions. This includes anything involving:
  - Reading, summarizing, or replying to emails
  - Sending emails or composing messages
  - HR tasks such as leave requests, recruitment, performance reviews, employee management, or HR-related communications

- **general** – if the message is a general question or unrelated to HR or email tasks.

Message: "{message}"

Respond with ONLY one lowercase word: hr_email_taskupdate or general.
"""

        ),
        HumanMessage(content=message),
    ]

    response = llm.invoke(messages).content.strip().lower()
    print(f"Analyzer Agent Response: {response}")

    return {
        **state,
        "classification": response,
        "current_agent": "analyzer"
    }

def task_assigner_agent(state: dict) -> dict:
    """Agent 2: Assigns the next agent based on message intent (task classification)"""

    message = state["message"]
    memory_context = state.get("memory_context", "")
    user_preferences = state.get("user_preferences", {})
    conversation_summary = state.get("conversation_summary", "")

    messages = [
        SystemMessage(
    content=f"""You are a task classification agent with conversation memory.

CONVERSATION CONTEXT:
{conversation_summary}

MEMORY CONTEXT:
{memory_context}

USER PREFERENCES:
{json.dumps(user_preferences, indent=2)}

Based on the conversation history and current message, assign the task to the correct agent:

Your job is to read the user's message and assign it to the correct task agent.

Classify the message into one of the following **task_classification** categories:

1. **email_fetcher&responder_agent** – if the message asks to:
   - Fetch, show, or summarize emails
   - Reply to or respond to an email
   - Provide latest emails or email updates

2. **job_applications_emails_summary_agent** – if the message asks to:
   - Read, analyze, or summarize job application emails
   - List how many are from job applicants, which companies sent them, etc.

3. **job_application_screening_agent** – if the message asks to:
   - Screen job applications using a job description
   - Shortlist candidates based on resumes
   - Check who matches the job role, skills, etc.

4. **email_team_agent** – if the message asks to:
   - Send emails to candidates
   - Email wrong application candidates
   - Send rejection or acceptance emails
   - Email shortlisted or rejected candidates
   - Communicate with applicants via email

5. **other** – if the message does not match any of the above tasks.

Respond with ONLY one lowercase word:
email_fetcher&responder_agent, job_applications_emails_summary_agent, job_application_screening_agent, email_team_agent, or other.
"""
),
        HumanMessage(content=message),
    ]

    response = llm.invoke(messages).content.strip().lower()
    print(f"Task Assigner Agent Response: {response}")

    return {
        **state,
        "task_classification": response,
        "current_agent": "task_assigner"
    }



def email_fetcher_responder_agent(state: AgentState) -> AgentState:
    session_id = state.get("session_id")
    user_message = state.get("message")
   
    memory_context = state.get("memory_context", "")
    user_preferences = state.get("user_preferences", {})

    # Step 1: Fetch emails via utils
    email_data = email_fetcher(session_id=session_id)

    # Step 2: Prepare prompt
    system_prompt = f"""
You are an intelligent email summarizer with conversation memory.

CONVERSATION CONTEXT:
{memory_context}

USER PREFERENCES:
{json.dumps(user_preferences, indent=2)}

Based on our conversation history, provide a personalized email summary.

User's current request: "{user_message}"

Below is a list of the latest emails in JSON format. Your task is to read and analyze them, and write a **short summary** of what kind of emails were received.

Group similar emails (e.g. job applications, alerts, HR emails). Mention the count and sender types if possible.

Also consider the user's input: "{user_message}"

Respond with a brief, useful summary.
"""

    messages = [
        SystemMessage(content=system_prompt.strip()),
        HumanMessage(content=str(email_data)),
    ]

    # Step 3: Call LLM
    response = llm.invoke(messages)
    ai_response = response.content.strip()

    # Step 4: Return updated AgentState
    return {
        **state,
        "emails": email_data,
        "ai_response": ai_response,
        "current_agent": "email_fetcher&responder_agent"

    }


def job_applications_emails_summary_agent(state: AgentState) -> AgentState:
    from .utils import get_job_application_emails_as_json
    from langchain_core.messages import SystemMessage, HumanMessage

    session_id = state["session_id"]
    message = state["message"]
    


    job_emails = get_job_application_emails_as_json(session_id)

    if not job_emails:
        return {
            **state,
            "ai_response": "No job application emails found.",
            "current_agent": "job_applications_emails_summary_agent"
        }

    prompt = f"""
You are an intelligent email summarizer for HR job application emails.

The user asked: "{message}"

Below are the job application emails in JSON format.

Please summarize them with the following structure:

1. First, mention how many job application emails there are.
2. Then list them as:
   email1: short one-line summary of that email (mention sender name, position if known, and company if mentioned),
   email2: ..., etc.

Make sure the output is structured and human-readable.

Emails:
{json.dumps(job_emails, indent=2)}
"""

    messages = [
        SystemMessage(content="You summarize job application emails."),
        HumanMessage(content=prompt)
    ]

    summary = llm.invoke(messages).content.strip()

    return {
        **state,
        "ai_response": summary,
        "current_agent": "job_applications_emails_summary_agent"
    }


def job_application_screening_agent(state: AgentState) -> AgentState:
    """
    Agent: Screens job application emails + resumes using job description in the user message.
    """
    session_id = state["session_id"]
    job_description = state["message"]

    try:
        result = screen_and_summarize_applications(session_id=session_id, job_descr=job_description)
        final_summary = result.get("final_summary", "")
    except Exception as e:
        final_summary = f"Error during screening: {str(e)}"

    return {
        **state,
        "ai_response": final_summary,
        "current_agent": "job_application_screening_agent",
    }

def email_team_agent(state: AgentState) -> AgentState:
    """
    Email Team Agent - Handles sending emails to candidates based on screening results
    """
    from .email_team_agent import email_team_main_agent
    
    session_id = state.get("session_id", "")
    user_message = state.get("message", "")
    
    print(f"🚀 Email Team Agent called with message: {user_message}")
    
    # Call the main email team agent function
    result = email_team_main_agent(session_id, user_message)
    
    # Format response for user
    if result["success"]:
        ai_response = f"""✅ {result['message']}

📊 Summary:
- Target: {result['target_key']} candidates
- Found: {result['candidates_found']} candidates
- Sent: {result['emails_sent']} emails
- Failed: {result['emails_failed']} emails

🎯 Suggested Next Tasks:
{chr(10).join([f"• {task}" for task in result['next_tasks']])}"""
    else:
        ai_response = f"""❌ {result['message']}

🎯 Suggested Next Tasks:
{chr(10).join([f"• {task}" for task in result['next_tasks']])}"""
    
    return {
        **state,
        "ai_response": ai_response,
        "current_agent": "email_team_agent",
        "email_results": result
    }
        

