# Storeapp/decorators.py
from functools import wraps
from django.http import HttpResponse
from .models import Customer, order

def reset_cart_count(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            try:
                # Retrieve the user's active (incomplete) order
                customer = request.user.customer
                active_order = order.objects.get(customer=customer, complete=False)

                # Clear the cart items (here, we delete them)
                active_order.orderitem_set.all().delete()

                # Mark the order as complete
                active_order.complete = True
                active_order.save()
                print("Cart cleared and order marked as complete.")
            except order.DoesNotExist:
                print("No active order found.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view
