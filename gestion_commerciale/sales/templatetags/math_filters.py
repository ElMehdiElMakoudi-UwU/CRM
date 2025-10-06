from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def sub(value, arg):
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def calc_total_ttc(items):
    total = 0
    for item in items:
        tax_rate = float(getattr(item.product, 'tax_rate', 0))
        total += float(item.quantity) * float(item.unit_price) * (1 + tax_rate / 100)
    return f"{total:.2f}"
