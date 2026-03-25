"""
FINDORA - Notification Engine
Gmail SMTP — images downloaded from Cloudinary URL and embedded as Base64
"""

import os
import re
import smtplib
import ssl
import base64
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime
from typing import Dict, Tuple, Optional
from dotenv import load_dotenv

load_dotenv()

GMAIL_ADDRESS  = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASSWORD", "")
FROM_NAME      = os.getenv("FROM_NAME", "Findora")
API_BASE       = os.getenv("API_BASE_URL", "http://localhost:8000")
ENABLED        = bool(GMAIL_ADDRESS and GMAIL_APP_PASS)

print("🔍 EMAIL DEBUG")
print("GMAIL_ADDRESS:", GMAIL_ADDRESS)
print("GMAIL_APP_PASS:", "SET" if GMAIL_APP_PASS else "NOT SET")
print("EMAIL ENABLED:", ENABLED)


def parse_contact(contact_info: str) -> Tuple[str, Optional[str]]:
    parts = [p.strip() for p in contact_info.split("|")]
    email = parts[0] if parts else ""
    phone = parts[1] if len(parts) > 1 and parts[1] else None
    return email, phone


def is_valid_email(s: str) -> bool:
    return bool(re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", s.strip()))


def load_image_from_url(url: str) -> Optional[Tuple[str, str, str]]:
    """
    Download image from a URL (Cloudinary or any https://).
    Returns (cid, base64_data, mime_type) or None on failure.
    """
    if not url or not url.startswith("http"):
        return None

    ext = url.split("?")[0].split(".")[-1].lower()
    if ext in ("jpg", "jpeg"):
        mime = "image/jpeg"
    elif ext == "png":
        mime = "image/png"
    elif ext == "webp":
        mime = "image/webp"
    else:
        mime = "image/jpeg"   # Cloudinary default

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Findora/3.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
        b64 = base64.b64encode(raw).decode("utf-8")
        # cid = last segment of URL path without extension, safe for MIME
        cid = re.sub(r"[^a-zA-Z0-9_]", "_", url.split("/")[-1].split("?")[0])
        return cid, b64, mime
    except Exception as e:
        print(f"   ⚠️  Could not download image: {url[:60]}… — {e}")
        return None


def build_contact_box(other_label: str, contact_info: str) -> str:
    email, phone = parse_contact(contact_info)
    phone_row = ""
    if phone:
        phone_row = f"""
    <tr><td style="padding-top:8px;">
      <p style="margin:0 0 2px;font-size:9px;font-weight:700;color:rgba(255,255,255,.45);letter-spacing:.1em;text-transform:uppercase;">Mobile</p>
      <p style="margin:0;font-size:14px;font-weight:600;color:#fff;">{phone}</p>
    </td></tr>"""
    return f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:18px;">
  <tr><td style="background:#1e3a5f;border-radius:9px;padding:13px 15px;">
    <p style="margin:0 0 8px;font-size:9px;font-weight:700;color:rgba(255,255,255,.55);letter-spacing:.1em;text-transform:uppercase;">Contact the {other_label} Person</p>
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td>
        <p style="margin:0 0 2px;font-size:9px;font-weight:700;color:rgba(255,255,255,.45);letter-spacing:.1em;text-transform:uppercase;">Email</p>
        <p style="margin:0;font-size:14px;font-weight:600;color:#7ab8ff;">{email}</p>
      </td></tr>{phone_row}
    </table>
  </td></tr></table>"""


def item_card_html(label: str, item: Dict, border_color: str, bg: str, img_cid: Optional[str]) -> str:
    def trunc(t, n=120):
        return (t[:n] + "...") if len(t) > n else t

    img_html = ""
    if img_cid:
        img_html = f"""
      <tr><td style="padding-top:10px;">
        <img src="cid:{img_cid}" alt="{item.get('title','')}"
          style="width:100%;max-height:220px;object-fit:cover;border-radius:7px;display:block;" />
      </td></tr>"""
    elif item.get("image_path", "").startswith("http"):
        # Fallback: use direct URL if embedding failed
        img_html = f"""
      <tr><td style="padding-top:10px;">
        <img src="{item['image_path']}" alt="{item.get('title','')}"
          style="width:100%;max-height:220px;object-fit:cover;border-radius:7px;display:block;" />
      </td></tr>"""

    return f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:12px;">
  <tr><td style="background:{bg};border-radius:9px;overflow:hidden;border-left:3px solid {border_color};">
    <table width="100%" cellpadding="0" cellspacing="0" style="padding:13px 15px;">
      <tr><td>
        <p style="margin:0 0 4px;font-size:9px;font-weight:700;color:#7a8eaa;letter-spacing:.1em;text-transform:uppercase;">{label}</p>
        <p style="margin:0 0 3px;font-size:14px;font-weight:600;color:#0f172a;">{item.get('title','—')}</p>
        <p style="margin:0 0 4px;font-size:12px;color:#5c718a;line-height:1.5;">{trunc(item.get('description',''))}</p>
        <p style="margin:0;font-size:11px;color:#7a8eaa;">&#128205; {item.get('location','—')}</p>
      </td></tr>
      {img_html}
    </table>
  </td></tr></table>"""


def build_html(recipient_role, recipient_item, matched_item, confidence, r_cid, m_cid):
    role_label  = "Lost"  if recipient_role == "lost"  else "Found"
    other_label = "Found" if recipient_role == "lost"  else "Lost"
    action_text = "may have been found" if recipient_role == "lost" else "may belong to someone"
    pct         = round(confidence * 100, 1)
    bar_color   = "#1a4d33" if confidence >= 0.9 else "#1e3a5f"
    bar_width   = round(pct)
    now         = datetime.now().strftime("%d %b %Y, %I:%M %p")

    your_card    = item_card_html(f"Your {role_label} Item",     recipient_item, "#c5d0e0", "#f0f2f5", r_cid)
    matched_card = item_card_html(f"Matched {other_label} Item", matched_item,  "#1e3a5f", "#eef1f7", m_cid)
    contact_box  = build_contact_box(other_label, matched_item.get("contact_info", "—"))

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Findora Match Alert</title></head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f2f5;padding:32px 0;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:14px;overflow:hidden;border:1px solid #dde3ed;max-width:560px;">

<tr><td style="background:#1e3a5f;padding:22px 26px;">
  <table cellpadding="0" cellspacing="0"><tr>
    <td style="width:34px;height:34px;background:rgba(255,255,255,0.12);border-radius:8px;text-align:center;vertical-align:middle;font-size:16px;">&#128269;</td>
    <td style="padding-left:10px;">
      <p style="margin:0;font-size:18px;font-style:italic;color:#fff;font-family:Georgia,serif;">Findora</p>
      <p style="margin:0;font-size:9px;color:rgba(255,255,255,0.55);letter-spacing:.1em;text-transform:uppercase;">AI Lost &amp; Found</p>
    </td>
  </tr></table>
</td></tr>

<tr><td style="background:#e8f2ec;padding:11px 26px;border-bottom:1px solid #b8ddc8;">
  <p style="margin:0;font-size:12.5px;font-weight:600;color:#1a4d33;">&#10003;&nbsp; AI Match Detected — {pct}% Confidence</p>
</td></tr>

<tr><td style="padding:24px 26px;">
  <p style="margin:0 0 5px;font-size:10px;font-weight:700;color:#7a8eaa;letter-spacing:.1em;text-transform:uppercase;">Match Alert</p>
  <p style="margin:0 0 14px;font-size:22px;font-style:italic;color:#0f172a;font-family:Georgia,serif;">Your {role_label} item {action_text}</p>
  <p style="margin:0 0 20px;font-size:13px;color:#5c718a;line-height:1.65;">Our AI found a potential match. Compare the images below and contact the other party to confirm.</p>

  {your_card}
  {matched_card}

  <p style="margin:0 0 6px;font-size:11.5px;font-weight:600;color:#2d4460;">Match Confidence: {pct}%</p>
  <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:18px;">
  <tr><td style="background:#eef1f7;border-radius:4px;height:6px;">
    <table width="{bar_width}%" cellpadding="0" cellspacing="0">
    <tr><td style="background:{bar_color};border-radius:4px;height:6px;"></td></tr>
    </table>
  </td></tr></table>

  {contact_box}

  <p style="margin:0;font-size:12px;color:#7a8eaa;line-height:1.65;">Reach out directly to confirm. If this is not your item, please ignore this email.</p>
</td></tr>

<tr><td style="background:#1e3a5f;padding:16px 26px;text-align:center;">
  <p style="margin:0 0 3px;font-size:14px;font-style:italic;color:#fff;font-family:Georgia,serif;">Findora</p>
  <p style="margin:0 0 4px;font-size:10px;color:#7a9bbf;">Intelligent Lost &amp; Found — Powered by AI</p>
  <p style="margin:0;font-size:10px;color:#4a6a8a;">Sent on {now}</p>
</td></tr>

</table>
</td></tr></table>
</body></html>"""


def build_text(recipient_role, recipient_item, matched_item, confidence):
    pct   = round(confidence * 100, 1)
    rl    = "Lost"  if recipient_role == "lost" else "Found"
    ol    = "Found" if recipient_role == "lost" else "Lost"
    email, phone = parse_contact(matched_item.get("contact_info", ""))
    phone_line = f"Mobile : {phone}" if phone else ""
    return f"""FINDORA — AI Match Alert ({pct}%)

Your {rl} item '{recipient_item.get('title')}' may have been matched.

YOUR {rl.upper()} ITEM: {recipient_item.get('title')}
{recipient_item.get('description','')}
Location : {recipient_item.get('location','')}

MATCHED {ol.upper()} ITEM: {matched_item.get('title')}
{matched_item.get('description','')}
Location : {matched_item.get('location','')}

CONTACT THE {ol.upper()} PERSON:
Email  : {email}
{phone_line}

— Findora AI Lost & Found
"""


def send_email(to_address, recipient_role, recipient_item, matched_item, confidence):
    print(f"📤 Attempting to send email to: {to_address}")

    if not ENABLED:
        print("❌ EMAIL NOT ENABLED — check GMAIL_ADDRESS and GMAIL_APP_PASSWORD env vars")
        return False

    rl      = "Lost" if recipient_role == "lost" else "Found"
    subject = f"Findora — Your {rl} item may have been matched ({round(confidence*100)}%)"

    # Download images from Cloudinary
    r_img = load_image_from_url(recipient_item.get("image_path", ""))
    m_img = load_image_from_url(matched_item.get("image_path", ""))
    r_cid = r_img[0] if r_img else None
    m_cid = m_img[0] if m_img else None

    try:
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"]    = f"{FROM_NAME} <{GMAIL_ADDRESS}>"
        msg["To"]      = to_address

        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(build_text(recipient_role, recipient_item, matched_item, confidence), "plain"))
        alt.attach(MIMEText(build_html(recipient_role, recipient_item, matched_item, confidence, r_cid, m_cid), "html"))
        msg.attach(alt)

        # Embed images with Content-ID
        for img_data in [r_img, m_img]:
            if img_data:
                cid, b64data, mime_type = img_data
                img_bytes = base64.b64decode(b64data)
                mime_img  = MIMEImage(img_bytes, _subtype=mime_type.split("/")[1])
                mime_img.add_header("Content-ID", f"<{cid}>")
                mime_img.add_header("Content-Disposition", "inline")
                msg.attach(mime_img)

        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as smtp:
            smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASS)
            smtp.sendmail(GMAIL_ADDRESS, to_address, msg.as_string())

        print(f"   ✅ Email sent → {to_address} (images embedded: {bool(r_cid or m_cid)})")
        return True

    except smtplib.SMTPAuthenticationError:
        print(f"   ❌ Gmail auth failed — check GMAIL_APP_PASSWORD is a valid App Password (not your login password)")
        return False
    except Exception as e:
        print(f"   ❌ Email failed → {to_address}: {e}")
        return False


def notify_match(lost_item: Dict, found_item: Dict, confidence: float):
    print(f"\n   📣 Notifying users ({round(confidence*100)}% match)...")

    lc = lost_item.get("contact_info", "").strip()
    fc = found_item.get("contact_info", "").strip()

    if lc:
        lost_email, _ = parse_contact(lc)
        if is_valid_email(lost_email):
            print(f"   → Lost user  : {lost_email}")
            send_email(lost_email, "lost", lost_item, found_item, confidence)
        else:
            print(f"   ⚠️  Invalid lost email: '{lost_email}'")
    else:
        print("   ⚠️  Lost item has no contact info")

    if fc:
        found_email, _ = parse_contact(fc)
        if is_valid_email(found_email):
            print(f"   → Found user : {found_email}")
            send_email(found_email, "found", found_item, lost_item, confidence)
        else:
            print(f"   ⚠️  Invalid found email: '{found_email}'")
    else:
        print("   ⚠️  Found item has no contact info")