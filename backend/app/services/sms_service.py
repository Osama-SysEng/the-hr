"""
The H.R - SMS Service using Twilio
"""

import os
from typing import Optional, List, Dict, Any
from twilio.rest import Client


class SMSService:
    def __init__(self):
        self.account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
        self.phone_number = os.environ.get("TWILIO_PHONE_NUMBER", "")
        self.client = None
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)

    def send_sms(self, to: str, body: str) -> Optional[str]:
        if not self.client:
            return None
        try:
            message = self.client.messages.create(body=body, from_=self.phone_number, to=to)
            return message.sid
        except Exception as e:
            print(f"SMS failed: {e}")
            return None

    def send_attendance_alert(self, phone: str, employee_name: str, status: str, date: str) -> Optional[str]:
        return self.send_sms(phone, f"[{status.upper()}] {employee_name}: {status} - {date}")

    def send_leave_notification(self, phone: str, employee_name: str, status: str) -> Optional[str]:
        return self.send_sms(phone, f"طلب إجازة {employee_name}: {status}")

    def send_payroll_notification(self, phone: str, employee_name: str, net_salary: float) -> Optional[str]:
        return self.send_sms(phone, f"صافي الراتب {employee_name}: {net_salary:,.2f} EGP")

    def send_bulk_sms(self, recipients: List[Dict[str, str]], template: str) -> Dict[str, Any]:
        sent, failed = 0, 0
        for r in recipients:
            if self.send_sms(r["phone"], template.format(**r)):
                sent += 1
            else:
                failed += 1
        return {"sent": sent, "failed": failed}
