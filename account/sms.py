# account/sms.py
import os
import ghasedakpack

API_KEY = os.environ.get("GHASEDAK_API_KEY", "")
_TEMPLATE = "verifyphone"

def send_otp_sms(phone: str, code: str) -> None:
    if not API_KEY:
        # در حالت توسعه، لاگ کن و رد شو
        print(f"[DEV SMS] To:{phone} Code:{code}")
        return
    sms = ghasedakpack.Ghasedak(API_KEY)
    sms.verification({'receptor': phone, 'type': '1', 'template': _TEMPLATE, 'param1': code})
