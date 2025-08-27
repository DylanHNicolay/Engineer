import smtplib
import ssl
import os
import asyncio
from email.message import EmailMessage

class EmailSender:
    def __init__(self):
        self.limit = 495
        self.counter = self.limit
        self.smtp_server = "smtp.gmail.com"
        self.port = 465  # For SSL
        self.sender_email = os.getenv("GMAIL_ADDRESS")
        self.password = os.getenv("GMAIL_APP_PASSWORD")
        self.lock = asyncio.Lock()
        self._task = None

    async def start(self):
        """Starts the background task to reset the counter daily."""
        if self._task is None:
            self._task = asyncio.create_task(self._reset_counter_daily())

    async def _reset_counter_daily(self):
        while True:
            await asyncio.sleep(86400)  # 24 hours
            async with self.lock:
                self.counter = self.limit
            print("Email counter has been reset.")

    async def send_email(self, receiver_email, subject, body):
        async with self.lock:
            if self.counter <= 0:
                return False, "Daily email limit reached. Please try again in 24 hours."
            
            # New detailed check for environment variables
            missing_vars = []
            if not self.sender_email:
                missing_vars.append("GMAIL_ADDRESS")
            if not self.password:
                missing_vars.append("GMAIL_APP_PASSWORD")

            if missing_vars:
                error_message = f"Email service is not configured. Missing environment variables: {', '.join(missing_vars)}."
                print(f"ERROR: {error_message}") # Also print to console for debugging
                return False, error_message

            msg = EmailMessage()
            msg.set_content(body)
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = receiver_email

            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._send_smtp, msg)
                self.counter -= 1
                print(f"Email sent to {receiver_email}. Remaining emails: {self.counter}")
                return True, "Email sent successfully."
            except Exception as e:
                print(f"Error sending email: {e}")
                return False, "Failed to send verification email."
    
    def _send_smtp(self, msg):
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(self.smtp_server, self.port, context=context) as server:
            server.login(self.sender_email, self.password)
            server.send_message(msg)

email_sender = EmailSender()
