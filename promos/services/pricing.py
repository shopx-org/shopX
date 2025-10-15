# promos/services/pricing.py
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.core.cache import cache
from promos.models import Campaign, Coupon
from typing import List, Optional

D100 = Decimal("100")
D0 = Decimal("0")
D001 = Decimal("0.01")

@dataclass
class PricingLine:
    product_id: int
    category_id: int
    unit_price: Decimal
    quantity: int
    brand_id: Optional[int] = None  # ← جدید (اختیاری)
    extra_category_ids: List[int] = field(default_factory=list)  # ← جدید
    line_subtotal: Decimal = field(init=False)
    line_discount: Decimal = D0

    def __post_init__(self):
        if not isinstance(self.unit_price, Decimal):
            self.unit_price = Decimal(str(self.unit_price))
        self.line_subtotal = self.unit_price * self.quantity
@dataclass
class PricingResult:
    lines: list
    subtotal: Decimal
    total_discount: Decimal
    cart_discount: Decimal
    shipping_discount: Decimal
    total: Decimal
    explain: dict

class _ActiveProvider:
    KEY = "promos:active:{channel}"

    def get(self, channel="web", now=None):
        now = now or timezone.now()
        key = self.KEY.format(channel=channel)
        data = cache.get(key)
        if data is None:
            data = list(
                Campaign.objects.filter(
                    is_active=True, starts_at__lte=now, ends_at__gte=now, channel=channel
                )
                .prefetch_related("rules", "actions")
                .order_by("-priority", "id")
            )
            cache.set(key, data, 60)
        return data

class _Resolver:
    def pick(self, camps):
        ex = [c for c in camps if c.exclusive]
        return [ex[0]] if ex else camps

class PricingEngine:
    def __init__(self, provider=None, resolver=None):
        self.provider = provider or _ActiveProvider()
        self.resolver = resolver or _Resolver()

    def evaluate(self, lines, ctx: dict) -> PricingResult:
        now = timezone.now()
        camps = self.provider.get(ctx.get("channel", "web"), now)

        # کوپن‌ها → بالای لیست
        codes = ctx.get("coupons") or []
        if codes:
            for cp in Coupon.objects.filter(code__in=codes, is_active=True):
                if cp.is_running(now) and cp.campaign and cp.campaign.is_running(now):
                    camps.insert(0, cp.campaign)

        qualified = [c for c in camps if self._ok(c, lines)]
        picked = self.resolver.pick(qualified)

        cart_disc: Decimal = D0
        ship_disc: Decimal = D0
        explain = {"applied": [], "skipped": []}

        subtotal: Decimal = sum((l.line_subtotal for l in lines), D0)  # ← خروجی حتماً Decimal

        for c in picked:
            for a in c.actions.all():
                tag = f"{c.name}:{a.kind}:{a.scope}"

                # ---- LINE scope
                if a.scope == "line":
                    base = subtotal
                    if base <= 0:
                        continue
                    if a.kind == "percent_off":
                        if a.value is None:
                            continue
                        amt = base * (Decimal(a.value) / D100)
                    elif a.kind == "amount_off":
                        if a.value is None:
                            continue
                        amt = Decimal(a.value)
                    else:
                        amt = D0
                    amt = min(amt, Decimal(a.cap)) if a.cap is not None else amt
                    self._spread(lines, amt)
                    explain["applied"].append({"tag": tag, "amount": str(amt)})

                # ---- CART scope
                elif a.scope == "cart":
                    base = subtotal
                    if a.kind == "percent_off":
                        if a.value is None:
                            continue
                        amt = base * (Decimal(a.value) / D100)
                    elif a.kind == "amount_off":
                        if a.value is None:
                            continue
                        amt = Decimal(a.value)
                    else:
                        amt = D0
                    amt = min(amt, Decimal(a.cap)) if a.cap is not None else amt
                    cart_disc += amt
                    explain["applied"].append({"tag": tag, "amount": str(amt)})

                # ---- SHIPPING scope
                elif a.scope == "shipping":
                    if a.kind == "free_shipping":
                        amt = Decimal("999999999")  # downstream تفسیر می‌شود
                    elif a.kind == "amount_off":
                        if a.value is None:
                            continue
                        amt = Decimal(a.value)
                    else:
                        amt = D0
                    amt = min(amt, Decimal(a.cap)) if a.cap is not None else amt
                    ship_disc += amt
                    explain["applied"].append({"tag": tag, "amount": str(amt)})

        line_disc: Decimal = sum((l.line_discount for l in lines), D0)
        total_disc: Decimal = line_disc + cart_disc + ship_disc

        # جمع نهایی (بدون هزینه ارسال؛ ship_disc فقط برای گزارش)
        total: Decimal = (subtotal - line_disc - cart_disc).quantize(D001, rounding=ROUND_HALF_UP)
        subtotal = subtotal.quantize(D001, rounding=ROUND_HALF_UP)
        total_disc = total_disc.quantize(D001, rounding=ROUND_HALF_UP)

        return PricingResult(
            lines=lines,
            subtotal=subtotal,
            total_discount=total_disc,
            cart_discount=cart_disc,
            shipping_discount=ship_disc,
            total=total,
            explain=explain,
        )

    def _ok(self, c, lines) -> bool:
        for r in c.rules.all():
            p = r.payload or {}
            if r.kind == "product_in":
                ids = set(p.get("product_ids", []))
                if not any(l.product_id in ids for l in lines):
                    return False

            elif r.kind == "category_in":
                ids = set(p.get("category_ids", []))

                # دسته اصلی یا دسته‌های اضافی
                def in_any_cat(line):
                    if line.category_id in ids:
                        return True
                    if getattr(line, "extra_category_ids", None):
                        return any(cid in ids for cid in line.extra_category_ids)
                    return False

                if not any(in_any_cat(l) for l in lines):
                    return False

            elif r.kind == "cart_min_total":
                thr = Decimal(str(p.get("threshold", "0")))
                sub = sum((l.line_subtotal for l in lines), D0)
                if sub < thr:
                    return False

            elif r.kind == "qty_at_least":
                q = int(p.get("qty", 1))
                if not any(l.quantity >= q for l in lines):
                    return False

                # (اختیاری) اگر Rule برند را هم بخواهی، این‌را اضافه کن:
            elif r.kind == "brand_in":
                ids = set(p.get("brand_ids", []))
                if not any(getattr(l, "brand_id", None) in ids for l in lines):
                    return False

            return True

    def _spread(self, lines, amount: Decimal):
        """توزیع تخفیف خطی به نسبت subtotal."""
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        base = sum((l.line_subtotal for l in lines), D0)
        if base <= 0 or amount <= 0:
            return
        for l in lines:
            share = (l.line_subtotal / base) * amount
            l.line_discount += share
