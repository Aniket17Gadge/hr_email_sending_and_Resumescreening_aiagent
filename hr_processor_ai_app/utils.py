import os
import imaplib
import email
from email.header import decode_header
from django.core.files.base import ContentFile
from django.utils.timezone import is_naive, make_aware
from dotenv import load_dotenv
from .models import EmailRecord, EmailAttachment
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from .models import EmailRecord, EmailAttachment
import fitz  # PyMuPDF
import docx
import json
from .models import JobApplicationScreeningResult
from django.utils import timezone
import re

# Load environment variables first
load_dotenv()

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini LLM after loading env vars
llm = ChatGoogleGenerativeAI(
    model="models/gemini-2.0-flash",
    temperature=0.7,
    google_api_key=GEMINI_API_KEY
)

def clean_subject(subject):
    if subject is None:
        return ""
    decoded, encoding = decode_header(subject)[0]
    if isinstance(decoded, bytes):
        return decoded.decode(encoding or "utf-8", errors="ignore")
    return decoded

def classify_email_type_with_llm(subject: str, body: str) -> str:
    prompt = f"""
You are an email classification assistant. Based on the subject and body, classify this email as one of:
- job_application
- security
- organization
- other

Respond with ONLY one lowercase word.

Subject: {subject}
Body: {body}
"""

    messages = [
        SystemMessage(content="Classify this email."),
        HumanMessage(content=prompt)
    ]

    try:
        response = llm.invoke(messages).content.strip().lower()
        valid_types = ["job_application", "security", "organization", "other"]
        return response if response in valid_types else "other"
    except Exception:
        return "other"

def email_fetcher(session_id: str):
    mail = imaplib.IMAP4_SSL(EMAIL_HOST)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")

    status, messages = mail.search(None, "ALL")
    email_ids = messages[0].split()

    all_emails = []

    for email_id in email_ids[-10:]:  # Only latest 10 emails
        status, msg_data = mail.fetch(email_id, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])

                subject = clean_subject(msg.get("Subject"))
                sender = msg.get("From")
                to = msg.get("To")
                date_str = msg.get("Date")
                date_obj = email.utils.parsedate_to_datetime(date_str)
                if is_naive(date_obj):
                    date_obj = make_aware(date_obj)

                # Get plain text body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                            try:
                                body = part.get_payload(decode=True).decode()
                                break
                            except Exception:
                                continue
                else:
                    try:
                        body = msg.get_payload(decode=True).decode()
                    except Exception:
                        body = ""

                # Classify email type with LLM
                email_type = classify_email_type_with_llm(subject, body)

                # Save EmailRecord with email_type
                email_record = EmailRecord.objects.create(
                    session_id=session_id,
                    subject=subject,
                    sender=sender,
                    to=to,
                    date=date_obj,
                    body=body,
                    email_type=email_type,
                )

                attachments_data = []

                for part in msg.walk():
                    content_disposition = str(part.get("Content-Disposition"))
                    if "attachment" in content_disposition:
                        filename = part.get_filename()
                        if filename:
                            file_data = part.get_payload(decode=True)
                            attachment = EmailAttachment(
                                email=email_record,
                                session_id=session_id,
                                filename=filename,
                            )
                            attachment.file.save(filename, ContentFile(file_data))
                            attachments_data.append({
                                "filename": filename,
                                "url": attachment.file.url
                            })

                all_emails.append({
                    "id": email_record.id,
                    "session_id": session_id,
                    "subject": subject,
                    "sender": sender,
                    "to": to,
                    "date": date_obj.isoformat(),
                    "body": body,
                    "email_type": email_type,
                    "attachments": attachments_data,
                })

    mail.logout()
    print(f"Fetched {len(all_emails)} emails for session {session_id}")
    return all_emails


def get_job_application_emails_as_json(session_id: str) -> list:
    records = EmailRecord.objects.filter(session_id=session_id, email_type="job_application").order_by("-date")

    emails_json = [
        {
            "subject": r.subject,
            "sender": r.sender,
            "date": r.date.isoformat(),
            "body": r.body,
        }
        for r in records
    ]

    return emails_json


def extract_resume_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".pdf":
            text = ""
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text()
            return text.strip()
        elif ext in [".docx", ".doc"]:
            doc = docx.Document(file_path)
            return "\n".join(para.text for para in doc.paragraphs).strip()
    except Exception as e:
        print(f"Error extracting resume text from {file_path}: {e}")
    return ""

def screen_and_summarize_applications(session_id: str, job_descr: str):
    results = []

    # Fetch job application emails with email_type="job_application"
    records = EmailRecord.objects.filter(
        session_id=session_id,
        email_type="job_application"
    ).order_by("date")

    for email_record in records:
        # Extract resume text from attachments (take first non-empty)
        resume_text = ""
        attachments = EmailAttachment.objects.filter(email=email_record)
        for att in attachments:
            resume_text = extract_resume_text(att.file.path)
            if resume_text:
                break

        candidate_data = {
            "subject": email_record.subject,
            "body": email_record.body,
            "resume_text": resume_text,
        }

        # Prepare prompt for screening - More explicit JSON instructions
        prompt = f"""
You are an HR assistant helping to screen job applications.

Job Description:
{job_descr}

Candidate Application Details (subject, email body, resume text):
{json.dumps(candidate_data, indent=2)}

IMPORTANT: You must respond with ONLY a valid JSON object, no markdown, no explanations, no additional text.

Return exactly this format:
{{"screening_status": "shortlisted", "reason": "skill match"}}

Valid values:
- screening_status: "shortlisted" or "rejected" 
- reason: "skill match" or "skill mismatch" or "wrong application"

Screening Guidelines:
1. **Check Job Position Match**: First verify if the candidate is applying for the correct job position by comparing:
   - Job title/role mentioned in email body vs job description
   - If candidate applies for "Java Developer" but job is for "AI Developer" → "wrong application"
   - If candidate applies for "Marketing Manager" but job is for "Software Engineer" → "wrong application"

2. **For Correct Position Applications**: If applying for the right job, then evaluate skills:
   - Good skill match with job requirements → "shortlisted" with "skill match"
   - Poor skill match with job requirements → "rejected" with "skill mismatch"

3. **Consider both email body and resume**: Analyze both email content and resume for position match and skill evaluation

Examples:
- Job: AI Developer, Application: "I want to apply for Java Developer" → "wrong application"
- Job: Marketing Manager, Application: "Applying for Software Engineer role" → "wrong application"
- Job: AI Developer, Application: "Applying for AI Developer but no AI skills" → "skill mismatch"
"""

        try:
            response = llm.invoke([
                SystemMessage(content="You are a JSON-only response system. Return only valid JSON with no markdown formatting or additional text."),
                HumanMessage(content=prompt)
            ]).content.strip()

            # Clean the response - remove markdown code blocks if present
            if response.startswith('```json'):
                response = response.replace('```json', '').replace('```', '').strip()
            elif response.startswith('```'):
                response = response.replace('```', '').strip()
            
            # Try to extract JSON from response if it contains other text
            try:
                # Look for JSON-like pattern in the response
                import re
                json_match = re.search(r'\{.*?\}', response, re.DOTALL)
                if json_match:
                    response = json_match.group()
            except:
                pass

            # Validate JSON response
            resp_json = json.loads(response)
            
            # Ensure required keys exist with valid values
            if "screening_status" not in resp_json:
                resp_json["screening_status"] = "rejected"
            if "reason" not in resp_json:
                resp_json["reason"] = "error processing"
                
            # Validate screening_status values
            if resp_json["screening_status"] not in ["shortlisted", "rejected"]:
                resp_json["screening_status"] = "rejected"
                
            # Validate reason values
            valid_reasons = ["skill match", "skill mismatch", "wrong application", "error processing"]
            if resp_json["reason"] not in valid_reasons:
                resp_json["reason"] = "error processing"
                
        except (json.JSONDecodeError, ValueError) as e:
            print(f"LLM screening JSON error: {e}")
            print(f"Raw LLM response: {response}")
            resp_json = {
                "screening_status": "rejected",
                "reason": "error processing"
            }
        except Exception as e:
            print(f"LLM screening error: {e}")
            resp_json = {
                "screening_status": "rejected",
                "reason": "error processing"
            }

        # Save screening result to DB
        JobApplicationScreeningResult.objects.create(
            session_id=session_id,
            candidate_name=email_record.sender or "Unknown",
            candidate_email=email_record.sender or "Unknown",
            screening_status=resp_json["screening_status"],
            reason=resp_json["reason"],
            resume_text=resume_text,
            body=email_record.body or "",
            timestamp=timezone.now()
        )

        results.append({
            "candidate": email_record.sender or "Unknown",
            "email_body": email_record.body or "",
            **resp_json
        })

    # Create final summary prompt for LLM
    summary_prompt = f"""
Summarize the screening results below:

Results:
{json.dumps(results, indent=2)}

Output a short summary:
- Total applications: {len(results)}
- Shortlisted: {sum(1 for r in results if r['screening_status'] == 'shortlisted')}
- Rejected: {sum(1 for r in results if r['screening_status'] == 'rejected')}

Then list each candidate as follows:
Candidate 1:
- Email: ...
- Status: ...
- Reason: ...
"""

    try:
        final_summary = llm.invoke([
            SystemMessage(content="Summarize screening outcomes"),
            HumanMessage(content=summary_prompt)
        ]).content.strip()
    except Exception as e:
        print(f"LLM summary generation error: {e}")
        final_summary = "Failed to generate summary."

    return {
        "individual_results": results,
        "final_summary": final_summary
    }


# ============== EMAIL SENDING FUNCTIONS ==============

def extract_email_from_sender(sender_string):
    """
    Extract clean email from sender string like 'MJ D <abcde@gmail.com>'
    Returns: 'abcde@gmail.com'
    """
    if not sender_string:
        return ""
    
    # Look for email in angle brackets
    email_match = re.search(r'<([^>]+)>', sender_string)
    if email_match:
        return email_match.group(1).strip()
    
    # If no angle brackets, check if it's already a clean email
    if '@' in sender_string:
        return sender_string.strip()
    
    return ""


def fetch_candidates_by_target(session_id: str, target_key: str):
    """
    Fetch candidates data based on target key match only
    """
    try:
        # Get screening results based on target
        if target_key == "skill match":
            screening_records = JobApplicationScreeningResult.objects.filter(
                session_id=session_id,
                screening_status="shortlisted",
                reason="skill match"
            )
        else:
            screening_records = JobApplicationScreeningResult.objects.filter(
                session_id=session_id,
                screening_status="rejected",
                reason=target_key
            )
        
        candidates_json = []
        
        for record in screening_records:
            clean_email = extract_email_from_sender(record.candidate_email)
            
            # Get original email record for full details
            try:
                email_record = EmailRecord.objects.filter(
                    session_id=session_id,
                    sender__icontains=clean_email
                ).first()
                
                original_subject = email_record.subject if email_record else ""
                original_body = email_record.body if email_record else record.body
                original_date = email_record.date.isoformat() if email_record else ""
                
            except:
                original_subject = ""
                original_body = record.body
                original_date = ""
            
            candidates_json.append({
                "candidate_name": record.candidate_name or "Unknown",
                "candidate_email": clean_email,
                "screening_status": record.screening_status,
                "reason": record.reason,
                "resume_text": record.resume_text,
                "email_body": original_body,
                "original_subject": original_subject,
                "application_date": original_date,
                "screening_timestamp": record.timestamp.isoformat()
            })
        
        print(f"📊 Fetched {len(candidates_json)} candidates for '{target_key}'")
        return candidates_json
        
    except Exception as e:
        print(f"❌ Error fetching candidates: {e}")
        return []


def send_email_to_candidate(email: str, subject: str, body: str):
    """Send email to single candidate using Django's email backend"""
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        
        print(f"📧 Email sent successfully to {email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email to {email}: {e}")
        return False
