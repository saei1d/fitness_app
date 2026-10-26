from decimal import Decimal


def _money(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value or 0))


def _cap_pair(first: Decimal, second: Decimal, limit: Decimal):
    """کاهش از تخفیف دوم شروع می‌شود تا تخفیف پکیج، که زودتر اعمال شده، بماند."""
    if limit < 0:
        limit = Decimal("0")
    remaining = limit
    first_applied = min(first, remaining)
    remaining -= first_applied
    second_applied = min(second, remaining)
    return first_applied, second_applied


def split_purchase_amounts(
    *,
    total_amount,
    admin_commission,
    package_discount_amount=0,
    package_source=None,
    code_discount_amount=0,
    code_source=None,
):
    """سهم پلتفرم و فروشنده را جدا نگه می‌دارد.

    تخفیف باشگاه فقط از سهم فروشنده کم می‌شود و نمی‌تواند کمیسیون را صفر کند.
    تخفیف ادمین فقط از کمیسیون کم می‌شود و سهم فروشنده را بالا نمی‌برد.
    مبلغ نهایی برابر جمع همین دو سهم است، پس موقع تأیید کد از کیف پلتفرم
    بیشتر از پول دریافتی خارج نمی‌شود.
    """
    total_amount = _money(total_amount)
    admin_commission = _money(admin_commission)
    if admin_commission < 0:
        admin_commission = Decimal("0")

    seller_share = total_amount - admin_commission
    if seller_share < 0:
        seller_share = Decimal("0")

    package_discount_amount = _money(package_discount_amount)
    code_discount_amount = _money(code_discount_amount)
    if package_discount_amount < 0:
        package_discount_amount = Decimal("0")
    if code_discount_amount < 0:
        code_discount_amount = Decimal("0")

    if package_source == "admin":
        package_admin = package_discount_amount
        package_seller = Decimal("0")
    elif package_discount_amount:
        package_admin = Decimal("0")
        package_seller = package_discount_amount
    else:
        package_admin = Decimal("0")
        package_seller = Decimal("0")

    if code_source == "admin":
        code_admin = code_discount_amount
        code_seller = Decimal("0")
    elif code_discount_amount:
        code_admin = Decimal("0")
        code_seller = code_discount_amount
    else:
        code_admin = Decimal("0")
        code_seller = Decimal("0")

    package_admin, code_admin = _cap_pair(package_admin, code_admin, admin_commission)
    package_seller, code_seller = _cap_pair(package_seller, code_seller, seller_share)

    commission_amount = admin_commission - (package_admin + code_admin)
    net_amount = seller_share - (package_seller + code_seller)
    final_amount = commission_amount + net_amount
    package_applied = package_admin + package_seller
    code_applied = code_admin + code_seller
    return commission_amount, net_amount, final_amount, package_applied, code_applied
