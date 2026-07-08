import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException


def send_otp_email(to_email: str, otp: str, purpose: str = "verification") -> bool:
    """Send OTP to user's email via Brevo"""
    api_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("BREVO_SENDER_EMAIL", "noreply@example.com")
    sender_name = os.getenv("BREVO_SENDER_NAME", "ScanMyTooth")

    if not api_key:
        print("WARNING: BREVO_API_KEY not set. OTP email not sent.")
        return False

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = api_key

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    subject = f"Your ScanMyTooth OTP for {purpose}"
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; max-width: 480px; margin: auto; padding: 32px;">
        <h2 style="color: #01696f;">ScanMyTooth</h2>
        <p>Your One-Time Password (OTP) for <strong>{purpose}</strong> is:</p>
        <div style="font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #01696f; 
                    background: #f0f9f9; padding: 16px 24px; border-radius: 8px; 
                    text-align: center; margin: 24px 0;">
          {otp}
        </div>
        <p style="color: #666;">This OTP is valid for <strong>10 minutes</strong>. Do not share it with anyone.</p>
        <p style="color: #999; font-size: 12px;">If you did not request this, please ignore this email.</p>
      </body>
    </html>
    """

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        sender={"name": sender_name, "email": sender_email},
        subject=subject,
        html_content=html_content,
    )

    try:
        api_instance.send_transac_email(send_smtp_email)
        print(f"OTP email sent to {to_email}")
        return True
    except ApiException as e:
        print(f"Brevo API error sending OTP email: {e}")
        return False
