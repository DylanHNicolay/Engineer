import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Send verification email
def send_verification_email(rcsid, verification_code, sw):
    if sw == 1:
        email = f"{rcsid}@rpi.edu"
    else:
        email = f"{rcsid}"
    message = MIMEMultipart()
    message['From'] = os.getenv("GMAIL")
    message['To'] = email
    message["Subject"] = "Verification Code"
    message.attach(MIMEText(f'Your verification code is: {verification_code}', "plain"))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(os.getenv("GMAIL"), os.getenv("GMAIL_PASS"))
        server.sendmail(os.getenv("GMAIL"), email, message.as_string())
        print(f"Email successfully sent to {email}")
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
    finally:
        try:
            server.quit()
        except Exception as quit_error:
            print(f"Failed to close the connection properly: {quit_error}")
    return True