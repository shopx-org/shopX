# orders/services/zarinpal.py
import requests
from django.conf import settings


class ZarinpalClient:
    def __init__(self):
        self.merchant_id = settings.ZARINPAL_MERCHANT_ID
        self.request_url = settings.ZARINPAL_REQUEST_URL
        self.verify_url = settings.ZARINPAL_VERIFY_URL
        self.startpay_url = settings.ZARINPAL_STARTPAY_URL

    def request_payment(self, *, amount, callback_url, description, mobile=None, email=None):
        payload = {
            "merchant_id": self.merchant_id,
            "amount": int(amount),
            "description": description,
            "callback_url": callback_url,
            "metadata": {},
        }
        if mobile:
            payload["metadata"]["mobile"] = mobile
        if email:
            payload["metadata"]["email"] = email

        res = requests.post(self.request_url, json=payload, timeout=15)
        data = res.json()

        if data.get("errors"):
            return {"ok": False, "error": data["errors"]}

        d = data["data"]
        return {
            "ok": d.get("code") == 100,
            "code": d.get("code"),
            "authority": d.get("authority"),
            "pay_url": self.startpay_url + d.get("authority"),
        }

    def verify_payment(self, *, authority, amount):
        payload = {
            "merchant_id": self.merchant_id,
            "amount": int(amount),
            "authority": authority,
        }
        res = requests.post(self.verify_url, json=payload, timeout=15)
        data = res.json()

        if data.get("errors"):
            return {"ok": False, "error": data["errors"]}

        d = data["data"]
        return {
            "ok": d.get("code") == 100,
            "code": d.get("code"),
            "ref_id": d.get("ref_id"),
            "card_pan": d.get("card_pan"),
        }
