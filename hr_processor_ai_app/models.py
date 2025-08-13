# models.py
from django.db import models

class EmailRecord(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit primary key
    session_id = models.CharField(max_length=100)  # Track per session
    subject = models.CharField(max_length=500)
    sender = models.EmailField()
    to = models.TextField()
    date = models.DateTimeField()
    body = models.TextField()
    email_type = models.CharField(max_length=50, default="other")


    def __str__(self):
        return f"{self.subject} - {self.sender}"


class EmailAttachment(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit primary key
    email = models.ForeignKey(EmailRecord, related_name='attachments', on_delete=models.CASCADE)
    session_id = models.CharField(max_length=100)  # Same session ID for attachment
    filename = models.CharField(max_length=255)
    file = models.FileField(upload_to="email_attachments/")

    def __str__(self):
        return self.filename
    
class JobApplicationScreeningResult(models.Model):
    session_id = models.CharField(max_length=100)
    candidate_name = models.CharField(max_length=255)
    candidate_email = models.EmailField()
    screening_status = models.CharField(max_length=20)  # shortlisted / rejected
    reason = models.TextField()
    body = models.TextField()
    resume_text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.candidate_name} - {self.screening_status}"
