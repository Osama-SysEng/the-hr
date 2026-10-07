"""
The H.R - Email Service
Send emails for notifications, payslips, reports, invitations
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class EmailMessage:
    to: str
    subject: str
    body: str
    html_body: Optional[str] = None
    attachments: Optional[List[str]] = None  # List of file paths


class EmailService:
    """
    Email Service for sending notifications and documents.
    Supports SMTP sending with TLS.
    """

    def __init__(self):
        self.smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_user = os.environ.get("SMTP_USER", "")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "")
        self.from_address = os.environ.get("FROM_EMAIL", self.smtp_user)
        self.use_tls = True

        self.smtp_client = None

    def connect(self) -> bool:
        """Establish SMTP connection."""
        if not self.smtp_user or not self.smtp_password:
            return False

        try:
            self.smtp_client = smtplib.SMTP(self.smtp_host, self.smtp_port)
            self.smtp_client.starttls()
            self.smtp_client.login(self.smtp_user, self.smtp_password)
            return True
        except Exception as e:
            print(f"Email connection failed: {e}")
            return False

    def disconnect(self):
        """Close SMTP connection."""
        if self.smtp_client:
            try:
                self.smtp_client.quit()
            except Exception:
                pass
            self.smtp_client = None

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        attachments: Optional[List[str]] = None,
    ) -> bool:
        """
        Send an email.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Plain text body
            html_body: HTML body (optional)
            attachments: List of file paths to attach (optional)
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.smtp_user:
            print("Email service not configured")
            return False

        try:
            if not self.smtp_client or not self.smtp_client.ehlo():
                if not self.connect():
                    return False

            msg = MIMEMultipart("alternative")
            msg["From"] = self.from_address
            msg["To"] = to
            msg["Subject"] = subject

            # Attach plain text
            msg.attach(MIMEText(body, "plain", "utf-8"))

            # Attach HTML if provided
            if html_body:
                msg.attach(MIMEText(html_body, "html", "utf-8"))

            # Attach files
            if attachments:
                for attachment_path in attachments:
                    if os.path.exists(attachment_path):
                        with open(attachment_path, "rb") as f:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                "Content-Disposition",
                                f"attachment; filename={os.path.basename(attachment_path)}",
                            )
                            msg.attach(part)

            self.smtp_client.send_message(msg)
            return True

        except Exception as e:
            print(f"Failed to send email to {to}: {e}")
            return False

    def send_payslip_email(
        self,
        employee_email: str,
        employee_name: str,
        payroll_month: int,
        payroll_year: int,
        net_salary: float,
        payslip_path: Optional[str] = None,
    ) -> bool:
        """Send payslip to employee."""
        subject = f"كشف الراتب - {payroll_month}/{payroll_year}"
        
        body = f"""عزيزي {employee_name},

تم إعداد كشف راتبك لشهر {payroll_month}/{payroll_year}.
صافي الراتب: {net_salary:,.2f} EGP

يرجى العثور على كشف الراتب المرفق (إن وجد).

مع خالص التحية،
فريق الموارد البشرية - The H.R
"""

        html_body = f"""
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f5f5f5; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #0d6efd; margin-bottom: 20px; }}
                .salary {{ font-size: 24px; font-weight: bold; color: #28a745; margin: 20px 0; }}
                .footer {{ margin-top: 30px; color: #6c757d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>كشف الراتب الشهري</h1>
                <p>عزيزي {employee_name}،</p>
                <p>تم إعداد كشف راتبك لشهر {payroll_month}/{payroll_year}.</p>
                <p class="salary">صافي الراتب: {net_salary:,.2f} EGP</p>
                <p>يرجى العثور على كشف الراتب المرفق (إن وجد).</p>
                <p>للاستفسار، اتصل بفريق الموارد البشرية.</p>
                <div class="footer">
                    <p>مع خالص التحية،<br>فريق الموارد البشرية - The H.R</p>
                </div>
            </div>
        </body>
        </html>
        """

        return self.send_email(
            to=employee_email,
            subject=subject,
            body=body,
            html_body=html_body,
            attachments=[payslip_path] if payslip_path else None,
        )

    def send_interview_invitation(
        self,
        candidate_email: str,
        candidate_name: str,
        interview_url: str,
        job_title: str,
        expiration_hours: int = 48,
    ) -> bool:
        """Send AI interview invitation to candidate."""
        subject = f"دعوة مقابلة آلية - {job_title}"

        body = f"""عزيزي {candidate_name}،

تهانينا! تم اختيارك لمقابلة آلية لوظيفة {job_title}.

يمكنك إكمال المقابلة في أي وقت خلال {expiration_hours} ساعة من الآن.
المقابلة완전히 via النص والصوت (عربي/إنجليزي).

رابط المقابلة: {interview_url}

المقابلة تستغرق حوالي 10-15 دقيقة.
النتائج ست Reviewed بواسطة فريق HR.

مع خالص التحية،
فريق التوظيف - The H.R
"""
        return self.send_email(candidate_email, subject, body)

    def send_attendance_notification(
        self,
        manager_email: str,
        manager_name: str,
        employee_name: str,
        employee_number: str,
        attendance_status: str,
        date: str,
        details: str = "",
    ) -> bool:
        """Send attendance notification to manager."""
        subject = f"إشعار حضور - {employee_name} - {date}"

        body = f"""مدير مرموق،

يُعلمك فريق الحضور بتالية:

الموظف: {employee_name} ({employee_number})
التاريخ: {date}
الحالة: {attendance_status}
التفاصيل: {details}

يرجىTaking appropriate action.

مع خالص التحية،
نظام الحضور التلقائي - The H.R
"""
        return self.send_email(manager_email, subject, body)

    def send_leave_notification(
        self,
        employee_email: str,
        employee_name: str,
        leave_type: str,
        start_date: str,
        end_date: str,
        status: str,
        approver_name: Optional[str] = None,
    ) -> bool:
        """Send leave request status to employee."""
        subject = f"حالة طلب الإجازة - {leave_type}"

        if status == "approved":
            body = f"""عزيزي {employee_name}،

تمت الموافقة على طلب إجازتك!

نوع الإجازة: {leave_type}
البداية: {start_date}
النهاية: {end_date}
تمت الموافقة من: {approver_name or 'فريق HR'}

مع خالص التحية،
فريق الموارد البشرية - The H.R
"""
        elif status == "rejected":
            body = f"""عزيزي {employee_name}،

لم يتمت الموافقة على طلب إجازتك.

نوع الإجازة: {leave_type}
البداية: {start_date}
النهاية: {end_date}
السبب: {approver_name or 'لم يتم تحديده'}

يمكنك请求 إعادة النظر إذا كنت ترغب.

مع خالص التحية،
فريق الموارد البشرية - The H.R
"""
        else:
            body = f"""عزيزي {employee_name}،

تم استلام طلب إجازتك وسيتم مراجعته قريباً.

نوع الإجازة: {leave_type}
البداية: {start_date}
النهاية: {end_date}

مع خالص التحية،
فريق الموارد البشرية - The H.R
"""
        return self.send_email(employee_email, subject, body)

    def send_bulk_email(
        self,
        recipients: List[Dict[str, str]],
        subject: str,
        body_template: str,
        html_template: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send bulk email to multiple recipients.
        recipients = [{"email": "...", "name": "...", "variables": {...}}]
        Returns stats: total, sent, failed
        """
        sent = 0
        failed = 0
        failed_emails = []

        for recipient in recipients:
            email = recipient["email"]
            name = recipient.get("name", "")
            variables = recipient.get("variables", {})

            # Replace variables in template
            personalized_body = body_template
            personalized_html = html_template

            for key, value in variables.items():
                placeholder = "{" + key + "}"
                personalized_body = personalized_body.replace(placeholder, str(value))
                if personalized_html:
                    personalized_html = personalized_html.replace(placeholder, str(value))

            # Replace name placeholder
            personalized_body = personalized_body.replace("{name}", name)
            if personalized_html:
                personalized_html = personalized_html.replace("{name}", name)

            if self.send_email(email, subject, personalized_body, personalized_html):
                sent += 1
            else:
                failed += 1
                failed_emails.append(email)

        return {
            "total": len(recipients),
            "sent": sent,
            "failed": failed,
            "failed_emails": failed_emails,
        }

    def test_connection(self) -> bool:
        """Test email server connection."""
        return self.connect() and self.disconnect() or True
