import imaplib
import email
from email.header import decode_header

def test_email_connection():
    # REPLACE WITH YOUR REAL EMAIL
    username = "aniketdas1711@gmail.com"
    # REPLACE WITH YOUR 16-CHARACTER APP PASSWORD (NOT YOUR MAIN PASSWORD)
    password = "dpoz wvsg etbo ooev" 

    try:
        print("Attempting to connect to Gmail...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(username, password)
        mail.select("inbox")
        
        print("Connected! Fetching latest 3 emails...")
        status, messages = mail.search(None, "UNSEEN") # Searches for unread
        
        # Get the latest 3 emails
        email_ids = messages[0].split()[-3:]
        
        for e_id in email_ids:
            res, msg_data = mail.fetch(e_id, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            subject = decode_header(msg["Subject"])[0][0]
            if isinstance(subject, bytes): subject = subject.decode()
            print(f"Found Email: {subject}")
            
        mail.logout()
        print("\nSUCCESS: Connection works and data is retrievable.")
        
    except Exception as e:
        print(f"\nFAILURE: Could not connect to email.")
        print(f"Error details: {e}")

if __name__ == "__main__":
    test_email_connection()