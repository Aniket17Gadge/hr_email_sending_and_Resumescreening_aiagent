import json
from langchain_core.messages import SystemMessage, HumanMessage
from .utils import fetch_candidates_by_target, send_email_to_candidate,llm

def target_identifier_agent(user_message: str):
    """
    Agent to identify target key from user message
    """
    prompt = f"""
    User message: "{user_message}"
    
    What type of candidates do they want to email?
    
    Respond with ONLY one of these exact phrases:
    - wrong application
    - skill mismatch  
    - skill match
    
    Examples:
    "send email to wrong application candidates" → wrong application
    "email rejected candidates" → skill mismatch
    "send email to shortlisted candidates" → skill match
    """
    
    try:
        response = llm.invoke([
            HumanMessage(content=prompt)
        ]).content.strip().lower()
        
        if "wrong application" in response:
            return "wrong application"
        elif "skill match" in response:
            return "skill match"
        else:
            return "skill mismatch"
            
    except Exception as e:
        print(f"❌ Error in target identifier: {e}")
        return "wrong application"  # default


def email_generator_agent(candidate_data: dict, user_message: str, target_key: str):
    """
    Generate personalized email for individual candidate based on their full details
    """
    prompt = f"""
    User request: "{user_message}"
    Target type: {target_key}
    
    Candidate Details:
    - Name: {candidate_data['candidate_name']}
    - Email: {candidate_data['candidate_email']}
    - Original Application Subject: {candidate_data['original_subject']}
    - Application Body: {candidate_data['email_body'][:500]}
    - Resume Summary: {candidate_data['resume_text'][:300]}
    - Screening Reason: {candidate_data['reason']}
    - Application Date: {candidate_data['application_date']}
    
    Generate a professional, personalized email for this specific candidate.
    
    Return ONLY JSON:
    {{
        "subject": "personalized subject line",
        "body": "personalized email body (use {candidate_data['candidate_name']} for name)"
    }}
    
    Guidelines:
    - Reference their original application if relevant
    - Be specific about their background/skills mentioned
    - For "wrong application": Mention the position mismatch specifically
    - For "skill mismatch": Be encouraging but honest about skill gaps
    - For "skill match": Mention specific skills that matched
    """
    
    try:
        response = llm.invoke([
            HumanMessage(content=prompt)
        ]).content.strip()
        
        # Clean response
        if response.startswith('```'):
            response = response.replace('```json', '').replace('```', '').strip()
        
        email_data = json.loads(response)
        return {
            "subject": email_data.get("subject", f"Regarding your application - {candidate_data['candidate_name']}"),
            "body": email_data.get("body", f"Dear {candidate_data['candidate_name']},\n\nThank you for your application.\n\nBest regards,\nHR Team")
        }
        
    except Exception as e:
        print(f"❌ Error generating email for {candidate_data['candidate_name']}: {e}")
        return {
            "subject": f"Application Update - {candidate_data['candidate_name']}",
            "body": f"Dear {candidate_data['candidate_name']},\n\nThank you for your application.\n\nBest regards,\nHR Team"
        }



def send_individual_email(candidate_data: dict, user_message: str, target_key: str):
    """
    Generate and send email to individual candidate
    """
    try:
        # Generate personalized email
        email_content = email_generator_agent(candidate_data, user_message, target_key)
        
        # Send email
        success = send_email_to_candidate(
            candidate_data["candidate_email"], 
            email_content["subject"], 
            email_content["body"]
        )
        
        return {
            "candidate_name": candidate_data["candidate_name"],
            "candidate_email": candidate_data["candidate_email"],
            "subject": email_content["subject"],
            "success": success,
            "error": None if success else "Failed to send"
        }
        
    except Exception as e:
        return {
            "candidate_name": candidate_data.get("candidate_name", "Unknown"),
            "candidate_email": candidate_data.get("candidate_email", "Unknown"),
            "subject": "",
            "success": False,
            "error": str(e)
        }


def email_sender_agent(candidates_json: list, email_content: dict):
    """
    Agent to send emails to all candidates
    """
    sent_count = 0
    failed_emails = []
    
    for candidate in candidates_json:
        try:
            # Personalize email
            personalized_body = email_content["body"].replace("{{candidate_name}}", candidate["candidate_name"])
            
            if send_email_to_candidate(
                candidate["candidate_email"], 
                email_content["subject"], 
                personalized_body
            ):
                sent_count += 1
            else:
                failed_emails.append(candidate["candidate_email"])
                
        except Exception as e:
            print(f"❌ Error sending to {candidate.get('candidate_email', 'unknown')}: {e}")
            failed_emails.append(candidate.get("candidate_email", "unknown"))
    
    return {
        "sent_count": sent_count,
        "failed_emails": failed_emails,
        "total_candidates": len(candidates_json)
    }


def response_generator_agent(send_results: dict, target_key: str):
    """
    Agent to generate final response message
    """
    prompt = f"""
    Email sending completed:
    - Target type: {target_key}
    - Sent successfully: {send_results['sent_count']}
    - Total candidates: {send_results['total_candidates']}
    - Failed: {len(send_results['failed_emails'])}
    
    Generate a professional response message and suggest 2-3 next tasks.
    
    Return ONLY JSON:
    {{
        "message": "success message",
        "next_tasks": ["task 1", "task 2", "task 3"]
    }}
    """
    
    try:
        response = llm.invoke([
            HumanMessage(content=prompt)
        ]).content.strip()
        
        if response.startswith('```'):
            response = response.replace('```json', '').replace('```', '').strip()
        
        response_data = json.loads(response)
        return response_data
        
    except Exception as e:
        print(f"❌ Error in response generator: {e}")
        return {
            "message": f"✅ Successfully sent emails to {send_results['sent_count']} {target_key} candidates.",
            "next_tasks": ["Review remaining candidates", "Schedule interviews", "Update job posting"]
        }


def email_team_main_agent(session_id: str, user_message: str):
    """
    Main email team agent with enhanced workflow
    """
    print(f"🚀 Email Team Agent started for session: {session_id}")
    print(f"📝 User message: {user_message}")
    
    # Step 1: Identify target key
    target_key = target_identifier_agent(user_message)
    print(f"🎯 Target identified: {target_key}")
    
    # Step 2: Fetch unique candidates with full details
    candidates_list = fetch_candidates_by_target(session_id, target_key)
    print(f"📊 Found {len(candidates_list)} unique candidates")
    
    if not candidates_list:
        return {
            "success": False,
            "message": f"No {target_key} candidates found in database.",
            "next_tasks": ["Check screening results", "Review applications"],
            "target_key": target_key,
            "candidates_found": 0,
            "emails_sent": 0,
            "emails_failed": 0,
            "detailed_results": []
        }
    
    # Step 3: Send emails in loop (one by one with personalization)
    detailed_results = []
    successful_sends = 0
    failed_sends = 0
    
    print(f"📤 Starting email sending loop for {len(candidates_list)} candidates...")
    
    for i, candidate in enumerate(candidates_list, 1):
        print(f"📧 Processing candidate {i}/{len(candidates_list)}: {candidate['candidate_name']}")
        
        # Generate and send individual email
        result = send_individual_email(candidate, user_message, target_key)
        detailed_results.append(result)
        
        if result["success"]:
            successful_sends += 1
            print(f"✅ Email sent to {result['candidate_name']}")
        else:
            failed_sends += 1
            print(f"❌ Failed to send to {result['candidate_name']}: {result['error']}")
    
    print(f"📊 Email sending complete: {successful_sends} sent, {failed_sends} failed")
    
    # Step 4: Generate final AI response using LLM
    final_response = generate_final_response(
        detailed_results, target_key, user_message, successful_sends, failed_sends
    )
    
    return {
        "success": successful_sends > 0,
        "target_key": target_key,
        "candidates_found": len(candidates_list),
        "emails_sent": successful_sends,
        "emails_failed": failed_sends,
        "detailed_results": detailed_results,
        "message": final_response["message"],
        "next_tasks": final_response["next_tasks"]
    }

def generate_final_response(detailed_results: list, target_key: str, user_message: str, sent_count: int, failed_count: int):
    """
    Generate comprehensive AI response using LLM
    """
    # Prepare summary for LLM
    successful_emails = [r for r in detailed_results if r["success"]]
    failed_emails = [r for r in detailed_results if not r["success"]]
    
    prompt = f"""
    User requested: "{user_message}"
    Target type: {target_key}
    
    Email Sending Results:
    - Total candidates: {len(detailed_results)}
    - Successfully sent: {sent_count}
    - Failed: {failed_count}
    
    Successful Emails:
    {json.dumps([{
        "name": r["candidate_name"], 
        "email": r["candidate_email"],
        "subject": r["subject"]
    } for r in successful_emails], indent=2)}
    
    Failed Emails:
    {json.dumps([{
        "name": r["candidate_name"], 
        "email": r["candidate_email"],
        "error": r["error"]
    } for r in failed_emails], indent=2)}
    
    Generate a comprehensive, professional response message that:
    1. Summarizes what was accomplished
    2. Lists who received emails (with their names)
    3. Mentions any failures
    4. Suggests 2-3 relevant next tasks
    
    Return ONLY JSON:
    {{
        "message": "detailed success message with names and specifics",
        "next_tasks": ["specific task 1", "specific task 2", "specific task 3"]
    }}
    """
    
    try:
        response = llm.invoke([
            HumanMessage(content=prompt)
        ]).content.strip()
        
        if response.startswith('```'):
            response = response.replace('```json', '').replace('```', '').strip()
        
        response_data = json.loads(response)
        return response_data
        
    except Exception as e:
        print(f"❌ Error generating final response: {e}")
        
        # Fallback response
        successful_names = [r["candidate_name"] for r in detailed_results if r["success"]]
        failed_names = [r["candidate_name"] for r in detailed_results if not r["success"]]
        
        message = f"✅ Email campaign completed for {target_key} candidates.\n\n"
        message += f"📊 Summary: {sent_count} emails sent successfully, {failed_count} failed.\n\n"
        
        if successful_names:
            message += f"✅ Emails sent to: {', '.join(successful_names[:5])}"
            if len(successful_names) > 5:
                message += f" and {len(successful_names)-5} others"
            message += "\n\n"
        
        if failed_names:
            message += f"❌ Failed to send to: {', '.join(failed_names)}\n\n"
        
        return {
            "message": message,
            "next_tasks": [
                "Review email delivery status",
                "Follow up with candidates who received emails",
                "Check and retry failed email addresses"
            ]
        }