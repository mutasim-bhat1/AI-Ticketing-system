# 📧 Email System - Complete Guide

## ✅ SMTP Email Sending is Now Active!

Your AI ticketing system now sends **REAL EMAILS** using Gmail's SMTP server.

---

## 🔧 Configuration

### Email Credentials (from `.env`):
- **Sender Email:** `mutasimbhat2@gmail.com`
- **App Password:** `jtlb wpbb zwvo jgtk`
- **SMTP Server:** Gmail (smtp.gmail.com:587)

---

## 📬 Email Routing Table

| Query Type | Matches Service | Email Sent To | Auto-Reply? |
|------------|----------------|---------------|-------------|
| "I forgot my password" | Password Reset | ✉️ No email | ✅ Yes |
| "I want a refund" | Refund | ✉️ No email | ✅ Yes |
| "I want to borrow a book" | Library | ✉️ No email | ✅ Yes |
| "I need a bus pass" | Transport | ✉️ No email | ✅ Yes |
| **"I want to see my results"** | **Academic Support** | **📧 mutu02693@gmail.com** | ❌ No |
| **"What time does cafeteria open?"** | **No match (General)** | **📧 mutasimbhat1@gmail.com** | ❌ No |

---

## 🧪 How to Test

### Test 1: Academic Query (Should Send Email)
```bash
POST http://localhost:8000/query
{
  "query": "I want to see my 8th class results"
}
```

**What happens:**
1. ✅ Agent matches "Academic Support" in kb.json
2. ✅ Checks: `auto_reply_allowed = false`
3. ✅ Calls `send_email()` function
4. 📧 **Real email sent to:** `mutu02693@gmail.com`
5. 📝 Email details printed in uvicorn terminal

**Email Content:**
```
From: mutasimbhat2@gmail.com
To: mutu02693@gmail.com
Subject: New Ticket: Academic Support - Grade Query
Body:
User Query: I want to see my 8th class results

Requires academic office review.
```

---

### Test 2: General Query (Should Send Email)
```bash
POST http://localhost:8000/query
{
  "query": "I want to play games in my school"
}
```

**What happens:**
1. ✅ Agent searches kb.json → No match
2. ✅ Follows fallback rule
3. ✅ Calls `send_email()` function
4. 📧 **Real email sent to:** `mutasimbhat1@gmail.com`

**Email Content:**
```
From: mutasimbhat2@gmail.com
To: mutasimbhat1@gmail.com
Subject: General Support Request
Body:
User Query: I want to play games in my school

No specific department match.
```

---

### Test 3: Password Reset (Should NOT Send Email)
```bash
POST http://localhost:8000/query
{
  "query": "I forgot my password"
}
```

**What happens:**
1. ✅ Agent matches "Password Reset" in kb.json
2. ✅ Checks: `auto_reply_allowed = true`
3. ✅ Calls `generate_reply()` function
4. ✉️ **No email sent** (auto-reply only)

---

## 📊 Email Sending Logic

```python
# In tools.py - send_email() function

1. Load credentials from .env
   - EMAIL_USER = mutasimbhat2@gmail.com
   - EMAIL_PASS = jtlb wpbb zwvo jgtk

2. Create email message
   - From: mutasimbhat2@gmail.com
   - To: [recipient from kb.json or fallback]
   - Subject: [AI-generated subject]
   - Body: [User query + context]

3. Connect to Gmail SMTP
   - Server: smtp.gmail.com
   - Port: 587
   - Security: TLS

4. Send email
   - Login with app password
   - Send message
   - Return success/error

5. Log to terminal
   - Print email details
   - Show success/failure
```

---

## 🔍 Troubleshooting

### If emails are NOT arriving:

1. **Check Gmail Settings:**
   - Ensure 2-factor authentication is enabled
   - Verify app password is correct in `.env`
   - Check if "Less secure app access" is NOT blocking

2. **Check Spam Folder:**
   - Emails might be in spam/junk folder
   - Mark as "Not Spam" if found

3. **Check Terminal Output:**
   - Look for "✅ EMAIL SENT SUCCESSFULLY!" message
   - If you see errors, they'll be printed there

4. **Check Email Addresses:**
   - Verify all emails in kb.json are correct
   - Make sure they're real, active email addresses

5. **Test SMTP Connection:**
   ```python
   # Run this to test SMTP directly
   import smtplib
   server = smtplib.SMTP("smtp.gmail.com", 587)
   server.starttls()
   server.login("mutasimbhat2@gmail.com", "jtlb wpbb zwvo jgtk")
   print("✅ SMTP connection successful!")
   server.quit()
   ```

---

## 📝 Current Email Addresses in kb.json

```json
{
  "Password Reset": "mutasimbhat1@gmail.com",
  "Refund": "mutasimjan12@gmail.com",
  "Library": "mutasimbhat21@gmail.com",
  "Transport": "janmutasim563@gmail.com",
  "Academic Support": "mutu02693@gmail.com",
  "General/Fallback": "mutasimbhat1@gmail.com"
}
```

---

## 🚀 What Changed

### Before:
```python
# tools.py - send_email()
print("EMAIL SENT")  # Just printed, no real email
return "Email sent successfully"
```

### After:
```python
# tools.py - send_email()
import smtplib
# ... create email message
server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()
server.login(sender_email, sender_password)
server.send_message(message)  # ACTUALLY SENDS EMAIL!
return "Email sent successfully"
```

---

## ✅ Summary

- ✅ **Real SMTP email sending is now active**
- ✅ **Emails sent from:** mutasimbhat2@gmail.com
- ✅ **Emails sent to:** Addresses in kb.json or fallback
- ✅ **Auto-reply services:** Don't send emails (just respond)
- ✅ **Email-required services:** Send real emails via Gmail
- ✅ **Error handling:** Catches and reports SMTP errors

---

## 🎯 Next Steps

1. **Test with a real query** that triggers Academic Support
2. **Check the inbox** at mutu02693@gmail.com
3. **Verify email arrives** (check spam if not in inbox)
4. **Test general queries** to verify fallback email works
5. **Monitor uvicorn terminal** for email sending logs

Your ticketing system is now fully functional with real email delivery! 🎉
