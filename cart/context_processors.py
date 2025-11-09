from .cart import Cart

def cart_badge(request):
    try:
        return {"cart_count": Cart(request).items_count()}
    except Exception:
        return {"cart_count": 0}
