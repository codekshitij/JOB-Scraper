#!/usr/bin/env python3
"""
Email Connection Test Script
Tests SMTP connection and email sending functionality
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded .env file")
except ImportError:
    print("⚠️ python-dotenv not installed. Using system environment variables.")
    print("💡 Install with: pip install python-dotenv")
except Exception as e:
    print(f"⚠️ Could not load .env file: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_email_connection():
    """Test email connection and send a test email"""
    
    print("🔍 Testing Email Configuration...")
    print("-" * 50)
    
    # Get email settings
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    email_user = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD")
    recipient_email = os.getenv("RECIPIENT_EMAIL")
    
    # Display configuration (hide password)
    print(f"📧 SMTP Server: {smtp_server}")
    print(f"🔌 SMTP Port: {smtp_port}")
    print(f"👤 Email User: {email_user}")
    print(f"🔐 Password: {'✅ Set' if email_password else '❌ Not Set'}")
    print(f"📬 Recipient: {recipient_email}")
    print()
    
    # Check if all required settings are present
    missing_settings = []
    if not smtp_server:
        missing_settings.append("SMTP_SERVER")
    if not smtp_port:
        missing_settings.append("SMTP_PORT")
    if not email_user:
        missing_settings.append("EMAIL_USER")
    if not email_password:
        missing_settings.append("EMAIL_PASSWORD")
    if not recipient_email:
        missing_settings.append("RECIPIENT_EMAIL")
    
    if missing_settings:
        print(f"❌ Missing required settings: {', '.join(missing_settings)}")
        print()
        print("💡 Set these environment variables:")
        for setting in missing_settings:
            print(f"   export {setting}='your_value'")
        return False
    
    print("✅ All email settings are configured")
    print()
    
    # Test SMTP connection
    server = None
    try:
        print("🔄 Step 1: Connecting to SMTP server...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.set_debuglevel(1)  # Enable debug output
        print("✅ Connected to SMTP server")
        
        print("\n🔄 Step 2: Starting TLS encryption...")
        server.starttls()
        print("✅ TLS encryption started")
        
        print("\n🔄 Step 3: Authenticating...")
        server.login(email_user, email_password)
        print("✅ Authentication successful")
        
        print("\n🔄 Step 4: Creating test email...")
        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = recipient_email
        msg['Subject'] = "🧪 Job Scraper Email Test - SUCCESS!"
        
        body = """
🎉 EMAIL TEST SUCCESSFUL! 🎉

Your job scraper email configuration is working correctly!

✅ SMTP connection: Working
✅ Authentication: Successful  
✅ Email sending: Functional

Your job scraper notifications should now work properly.

---
Sent from Job Scraper Email Test
Time: """ + str(os.popen('date').read().strip()) + """
Server: """ + smtp_server + ":" + str(smtp_port) + """
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        print("✅ Test email created")
        
        print("\n🔄 Step 5: Sending test email...")
        text = msg.as_string()
        server.sendmail(email_user, recipient_email, text)
        print("✅ Test email sent successfully!")
        
        print(f"\n🎉 SUCCESS! Check your inbox at {recipient_email}")
        print("📧 If you received the test email, your configuration is working!")
        
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Authentication Error: {e}")
        print("\n💡 Common fixes:")
        print("   • Make sure you're using an App Password (not regular password)")
        print("   • Enable 2-Factor Authentication on your Google account")
        print("   • Generate App Password: Google Account → Security → App passwords")
        print("   • Use the 16-character app password as EMAIL_PASSWORD")
        return False
        
    except smtplib.SMTPConnectError as e:
        print(f"❌ Connection Error: {e}")
        print(f"\n💡 Common fixes:")  
        print(f"   • Check SMTP server: {smtp_server}")
        print(f"   • Check SMTP port: {smtp_port}")
        print(f"   • Try port 465 with SSL instead of 587 with TLS")
        return False
        
    except smtplib.SMTPRecipientsRefused as e:
        print(f"❌ Recipient Error: {e}")
        print(f"\n💡 Check recipient email address: {recipient_email}")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False
        
    finally:
        if server:
            try:
                server.quit()
                print("\n📧 SMTP connection closed")
            except:
                pass

def show_gmail_setup_instructions():
    """Show detailed Gmail setup instructions"""
    print("\n" + "="*60)
    print("📧 GMAIL SETUP INSTRUCTIONS")
    print("="*60)
    print("""
1. 🔐 Enable 2-Factor Authentication:
   • Go to: https://myaccount.google.com/security
   • Turn on 2-Step Verification

2. 🔑 Generate App Password:
   • Go to: https://myaccount.google.com/apppasswords
   • Select app: "Mail"
   • Select device: "Other" → "Job Scraper"
   • Copy the 16-character password

3. 🌐 Set Environment Variables:
   export EMAIL_USER="your.email@gmail.com"
   export EMAIL_PASSWORD="abcd efgh ijkl mnop"  # 16-char app password
   export RECIPIENT_EMAIL="your.email@gmail.com"
   export SMTP_SERVER="smtp.gmail.com"
   export SMTP_PORT="587"

4. 🧪 Run this test again:
   python test_email.py
""")

if __name__ == "__main__":
    print("🧪 Job Scraper Email Connection Test")
    print("="*50)
    
    success = test_email_connection()
    
    if not success:
        show_gmail_setup_instructions()
    else:
        print("\n🎊 Your email configuration is ready!")
        print("🚀 Your job scraper should now send notifications successfully!")