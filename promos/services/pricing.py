# promos/services/pricing.py
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from django.utils import timezone
from django.core.cache import cache
from promos.models import Campaign, Coupon

D100 = Decimal("100")
D0 = Decimal("0")
D001 = Decimal("0.01")

@dataclass
class PricingLine:
    product_id: int
    category_id: int
    unit_price: Decimal
    quantity: int

    # اختیاری‌ها (برای قوانین/گزارش)
    variant_id: Optional[int] = None
    brand_id: Optional[int] = None
    extra_category_ids: List[int] = field(default_factory=list)

    # فلگ‌ها/مقادیر تخفیف در سطح واریانت/محصول (برای ساخت کمپین موقتی)
    _variant_sale_active: bool = False
    _variant_sale_percent: Optional[Decimal] = None
    _variant_sale_amount: Optional[Decimal] = None
    _product_sale_active: bool = False
    _product_sale_percent: Optional[Decimal] = None
    _product_sale_amount: Optional[Decimal] = None

    # ⬇️ اضافه کن:
    _exclude_from_discounts: bool = False

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
                ).prefetch_related("rules", "actions").order_by("-priority", "id")
            )
            cache.set(key, data, 60)
        return data


class _Resolver:
    def pick(self, camps):
        ex = [c for c in camps if getattr(c, "exclusive", False)]
        return [ex[0]] if ex else camps


class PricingEngine:
    def __init__(self, provider=None, resolver=None):
        self.provider = provider or _ActiveProvider()
        self.resolver = resolver or _Resolver()

    def evaluate(self, lines, ctx: dict) -> PricingResult:
        now = timezone.now()
        camps = self.provider.get(ctx.get("channel", "web"), now)

        # 1) کمپین‌های موقتی (مثلاً برای SALE مستقیمِ محصول/واریانت)
        ephemeral = ctx.get("ephemeral_campaigns") or []
        if ephemeral:
            camps = list(ephemeral) + list(camps)

        # helperهای امن برای ORM/ephemeral
        def _iter_actions(c):
            acts = getattr(c, "actions", None)
            if acts is None: return []
            if hasattr(acts, "all") and callable(acts.all):  # RelatedManager
                return acts.all()
            return acts  # list

        def _iter_rules(c):
            rules = getattr(c, "rules", None)
            if rules is None: return []
            if hasattr(rules, "all") and callable(rules.all):
                return rules.all()
            return rules

        def _ok_local(c, ls):
            for r in _iter_rules(c):
                p = getattr(r, "payload", {}) or {}
                kind = getattr(r, "kind", None)
                if kind == "product_in":
                    ids = set(p.get("product_ids", []))
                    if not any(l.product_id in ids for l in ls):
                        return False
                elif kind == "category_in":
                    ids = set(p.get("category_ids", []))
                    def in_any(line):
                        if line.category_id in ids:
                            return True
                        ec = getattr(line, "extra_category_ids", None)
                        return any(cid in ids for cid in (ec or []))
                    if not any(in_any(l) for l in ls):
                        return False
                elif kind == "cart_min_total":
                    thr = Decimal(str(p.get("threshold", "0")))
                    sub = sum((l.line_subtotal for l in ls), D0)
                    if sub < thr:
                        return False
                elif kind == "qty_at_least":
                    q = int(p.get("qty", 1))
                    if not any(l.quantity >= q for l in ls):
                        return False
                elif kind == "brand_in":
                    ids = set(p.get("brand_ids", []))
                    if not any(getattr(l, "brand_id", None) in ids for l in ls):
                        return False
            return True  # ← بیرون حلقه

        # 2) کوپن‌ها را در صدر بگذار
        codes = ctx.get("coupons") or []
        if codes:
            for cp in Coupon.objects.filter(code__in=codes, is_active=True):
                if cp.is_running(now) and cp.campaign and cp.campaign.is_running(now):
                    camps.insert(0, cp.campaign)

        # 3) فیلتر و انتخاب
        qualified = [c for c in camps if _ok_local(c, lines)]
        picked = self.resolver.pick(qualified)

        cart_disc = D0
        ship_disc = D0
        explain = {"applied": [], "skipped": []}
        subtotal: Decimal = sum((l.line_subtotal for l in lines), D0)

        for c in picked:
            for a in _iter_actions(c):
                kind = getattr(a, "kind", "")
                scope = getattr(a, "scope", "")
                val = getattr(a, "value", None)
                cap = getattr(a, "cap", None)
                tag = f"{getattr(c,'name','camp')}:{kind}:{scope}"

                if scope == "line":
                    eligible = [l for l in lines if not getattr(l, "_exclude_from_discounts", False)]
                    base = subtotal
                    if base <= 0:
                        continue
                    if kind == "percent_off" and val is not None:
                        amt = base * (Decimal(val) / D100)
                    elif kind == "amount_off" and val is not None:
                        amt = Decimal(val)
                    else:
                        amt = D0
                    if cap is not None: amt = min(amt, Decimal(cap))
                    self._spread(eligible, amt)
                    explain["applied"].append({"tag": tag, "amount": str(amt)})

                elif scope == "cart":
                    base = subtotal
                    if kind == "percent_off" and val is not None:
                        amt = base * (Decimal(val) / D100)
                    elif kind == "amount_off" and val is not None:
                        amt = Decimal(val)
                    else:
                        amt = D0
                    if cap is not None: amt = min(amt, Decimal(cap))
                    cart_disc += amt
                    explain["applied"].append({"tag": tag, "amount": str(amt)})

                elif scope == "shipping":
                    if kind == "free_shipping":
                        amt = Decimal("999999999")
                    elif kind == "amount_off" and val is not None:
                        amt = Decimal(val)
                    else:
                        amt = D0
                    if cap is not None: amt = min(amt, Decimal(cap))
                    ship_disc += amt
                    explain["applied"].append({"tag": tag, "amount": str(amt)})

        line_disc = sum((l.line_discount for l in lines), D0)
        total_disc = (line_disc + cart_disc + ship_disc).quantize(D001, rounding=ROUND_HALF_UP)
        subtotal = subtotal.quantize(D001, rounding=ROUND_HALF_UP)
        total = (subtotal - line_disc - cart_disc).quantize(D001, rounding=ROUND_HALF_UP)

        return PricingResult(
            lines=lines, subtotal=subtotal, total_discount=total_disc,
            cart_discount=cart_disc, shipping_discount=ship_disc,
            total=total, explain=explain
        )

    def _spread(self, lines, amount: Decimal):
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        base = sum((l.line_subtotal for l in lines), D0)
        if base <= 0 or amount <= 0:
            return
        for l in lines:
            l.line_discount += (l.line_subtotal / base) * amount
