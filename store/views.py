from django.contrib.auth import login,logout
from .models import order
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, F,Value, DecimalField
from django.db.models.functions import Cast
from django.db.models import CharField
import json
from django.http import JsonResponse
from django.conf import settings
import re
import stripe
from django.conf import settings
from django.shortcuts import redirect, reverse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Product,Category,orderitems, Customer,shippingaddress
from django.conf import settings
from django.urls import reverse
from .utils.email_service import send_email_brevo,send_email_sendgrid
from .utils.sms_service import send_sms,make_phonecall
from django.contrib import messages
import logging
from .forms import ProductForm
from django.shortcuts import render
from django.http import JsonResponse
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from .models import Product  # Update based on your actual imports

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


# Create your views here.
# def showprds(request):
#     if request.user.is_authenticated:
#         try:
#             # Customer already linked to this user
#             customer = request.user.customer
#         except Customer.DoesNotExist:
#             # Is there already a Customer with this email?
#             customer = Customer.objects.filter(email=request.user.email).first()
#             if customer:
#                 # Link the existing customer to this user
#                 customer.user = request.user
#                 customer.save()
#             else:
#                 # No customer exists at all, so create one
#                 customer = Customer.objects.create(
#                     user=request.user,
#                     name=request.user.username,
#                     email=request.user.email,)
#         ord, created = order.objects.get_or_create(
#             customer=customer,
#             complete=False )
#     else:
#         ord={"gettotalqty":0}
#
#     prds=Product.objects.all()
#     dict={"prds":prds,"order":ord}
#     return render(request,"store/home.html",dict)
def send_order_email(*args, **kwargs):

    if settings.EMAIL_PROVIDER == "brevo":
        return send_email_brevo(*args, **kwargs)

    elif settings.EMAIL_PROVIDER == "sendgrid":
        return send_email_sendgrid(*args, **kwargs)

    else:
        raise Exception("Unknown Email Provider")


def home(request):
    """
    Home page view with search, sorting, and pagination
    """
    # 1. Get parameters from request
    sort_order = request.GET.get('sort', 'sold_desc')  # Default sort by most sold
    search_string = request.GET.get('search', '').strip()
    page_number = request.GET.get('page', 1)

    if request.GET.get('search') is not None:
        page_number = 1

    if not search_string and 'search' in request.GET:
        return JsonResponse({'products': []})

    # 2. Build search filter
    filter_conditions = Q()
    if search_string:
        is_numeric = False
        search_price = None

        try:
            search_price = float(search_string)
            is_numeric = True
        except ValueError:
            pass

        search_conditions = Q()
        search_conditions |= Q(title__icontains=search_string) | Q(author__icontains=search_string)

        if is_numeric:
            search_conditions |= Q(price__gte=search_price - 1, price__lte=search_price + 1)

        filter_conditions = search_conditions
    # 3. Base queryset with Annotation
    # We traverse backwards from Product to 'orderitems', summing the 'quantity'.
    # We also add a filter inside the Sum to only count items where checked=True.
    # (You could also add orderitems__order__complete=True if needed)
    products = Product.objects.filter(filter_conditions).annotate(
        sold_count=Coalesce(
            Sum('orderitems__quantity', filter=Q(orderitems__order__complete=True)),
            0
        )
    )

    # 4. Apply sorting
    sort_mapping = {
        'title_asc': 'title',
        'title_desc': '-title',
        'author_asc': 'author',
        'author_desc': '-author',
        'price_asc': 'price',
        'price_desc': '-price',
        'sold_desc': '-sold_count',
        'sold_asc': 'sold_count',
    }

    order_by = sort_mapping.get(sort_order, '-sold_count')
    products = products.order_by(order_by)

    # 5. Pagination
    page_size = 8
    paginator = Paginator(products, page_size)
    try:
        p_products = paginator.get_page(page_number)
    except PageNotAnInteger:
        p_products = paginator.page(1)
    except EmptyPage:
        p_products = paginator.page(paginator.num_pages)

    # 6. Prepare context
    context = {
        'products': p_products,
        'page_obj': p_products,
        'page_index': int(page_number),
        'total_pages': paginator.num_pages,
        'has_previous': p_products.has_previous(),
        'has_next': p_products.has_next(),
        'current_sort': sort_order,
        'current_filter': search_string,
        'search_string': search_string,
        'total_items': paginator.count,
    }

    return render(request, 'store/home.html', context)


def edit_prodetails(request, pk):
    """
    View to edit an existing product's details from the frontend.
    Replaces the Django admin change form functionality.
    """
    # 1. Fetch the product using its primary key (ID)
    product = get_object_or_404(Product, id=pk)
    # 2. Handle form submission (Update button clicked)
    if request.method == 'POST':
        # Bind the form with POST data and FILES (for image updates)
        form = ProductForm(request.POST, request.FILES, instance=product)

        if form.is_valid():
            form.save()
            messages.success(request, f'"{product.title}" has been updated successfully!')
            return redirect('details')  # Redirects back to your Products Management page
        else:
            messages.error(request, 'There was an error updating the product. Please check the fields below.')

    # 3. Handle GET request (Page loaded to view the form)
    else:
        # Pre-fill the form with the product's current data
        form = ProductForm(instance=product)

    context = {
        'form': form,
        'product': product,
    }
    return render(request, 'store/edit_prodetails.html', context)


def update_product(request, pk):
    # 1. Fetch the exact product using its ID
    product = get_object_or_404(Product, id=pk)
    # 2. Handle form submission(When "Save Changes" is clicked)
    if request.method == 'POST':
        # request.FILES is required here to process image uploads
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'"{product.title}" was updated successfully!')
            return redirect('details')  # Redirects back to your Products Management page
        else:
            messages.error(request, 'Failed to update. Please check the form errors.')

    # 3. Handle page load (When "Update / Edit" is clicked from the list)
    else:
        # Pre-fills the form with current database values
        form = ProductForm(instance=product)

    context = {
        'form': form,
        'product': product,
    }
    return render(request, 'store/product_details.html', context)
@login_required(login_url='/myauth/login')
def updatecart(request):
    if request.method != "POST":
        return redirect("/myauth/login")
    customer = request.user.customer
    # 1. Find the most recent active cart for this customer
    order_obj = order.objects.filter(customer=customer, complete=False).order_by('-id').first()
    # 2. If the customer doesn't have an active cart, create a new one
    if not order_obj:
        order_obj = order.objects.create(customer=customer, complete=False)
    # Add to cart (from home page)
    btn_keys = [k for k in request.POST if k.startswith('btn') and k[3:].isdigit()]
    if btn_keys:
        pid = int(btn_keys[0][3:])
        product = Product.objects.get(id=pid)
        orderitem, _ = orderitems.objects.get_or_create(order=order_obj, product=product)
        orderitem.quantity += 1
        orderitem.save()
        return redirect("/cart/")
    # Update item (from cart page)
    if request.POST.get("btnupd"):
        item_id = request.POST.get("btnupd")  # this is the orderitem ID
        orderitem = orderitems.objects.get(id=item_id, order=order_obj)
        qty = int(request.POST.get(f"txtqty{item_id}", 1))
        if qty <= 0:
            orderitem.delete()
        else:
            orderitem.quantity = qty
            orderitem.checked = 'checked' + str(item_id) in request.POST
            orderitem.save()
        return redirect("/cart/")
    # Delete item (from cart page)
    if request.POST.get("btndel"):
        item_id = request.POST.get("btndel")
        orderitem = orderitems.objects.get(id=item_id, order=order_obj)
        orderitem.delete()
        return redirect("/cart/")

    return redirect("/cart/")

def get_selected_ids(request):
    """Return the list of OrderItem IDs that are currently selected."""
    return request.session.get('selected_item_ids', [])

def set_selected_ids(request, ids):
    """Store the list of selected OrderItem IDs in the session."""
    request.session['selected_item_ids'] = ids
    request.session.modified = True


 # or use @csrf_protect with proper token

@login_required
def update_cart_ajax(request):
    if request.method == 'POST':
        # Get the Order for the current user
        customer = request.user.customer
        ord,created = order.objects.get_or_create(customer=customer, complete=False)
        action = request.POST.get('action')
        item_id = int(request.POST.get('item_id'))
        if not item_id:
            return JsonResponse({'success': False, 'error': 'Missing item_id'})
        try:
            order_item = ord.orderitems_set.get(id=item_id)
        except orderitems.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Item not found'})
        selected_ids = set(get_selected_ids(request))  # helper must exist
        if action == 'toggle_selected':
            # Toggle the selection in session
            checked = request.POST.get('checked') == 'true'
            if checked:
                selected_ids.add(order_item.id)
            else:
                selected_ids.discard(order_item.id)
            set_selected_ids(request, list(selected_ids))
            # No DB change needed – selection is session‑only
        elif action == 'update_qty':
            new_qty = int(request.POST.get('qty', 1))
            if new_qty < 1:
                new_qty = 1
            order_item.quantity = new_qty
            order_item.save()
            # The selection state stays as is

        elif action == 'delete':
            # order_item.delete()
            # Also remove its ID from selected list if present
            selected_ids = set(get_selected_ids(request))
            order_item.delete()
            selected_ids.discard(order_item.id)
            set_selected_ids(request,list(selected_ids))
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action'})

        # Recalculate totals
        orditms = ord.orderitems_set.all()
        total_items = sum(item.quantity for item in orditms)
        total_price = sum(item.getitemtotal for item in orditms)  # assuming method exists

        # Compute line total for the updated item (if not deleted)
        item_total = None
        if action != 'delete':
            item_total = order_item.product.price * order_item.quantity
        return JsonResponse({
            'success': True,
            'total_items': total_items,
            'total_price': float(total_price),
            'item_total': float(item_total) if item_total is not None else None,
            'selected_ids': get_selected_ids(request),
        })
    return JsonResponse({'success': False}, status=400)
def cart(request):
    if request.user.is_authenticated:
        customer = request.user.customer
        ord, created = order.objects.get_or_create(customer=customer, complete=False)
        orditms = ord.orderitems_set.all()
        selected_ids = get_selected_ids(request)   # from your session helper

        # Compute totals
        total_quantity = sum(item.quantity for item in orditms)
        total_price = sum(item.getitemtotal for item in orditms)   # if getitemtotal is a method

        dict = {
            "orditms": orditms,
            "order": ord,
            "selected_ids": selected_ids,
            "total_quantity": total_quantity,
            "total_price": total_price,
        }
        return render(request, "store/cart.html", dict)
    else:
        return redirect("/myauth/login")


@login_required(login_url='/myauth/login')
def checkout(request):
    # 1. Get or create the active order for the logged-in user
    customer = request.user.customer
    # FIX: Use a consistent variable name 'ordr'
    ordr = order.objects.filter(customer=customer, complete=False).order_by('-id').first()

    # FIX: Use the same 'ordr' variable here
    if not ordr:
        ordr = order.objects.create(customer=customer, complete=False)
    # 2. Handle POST from the cart form
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_items')
        selected_ids = [int(id) for id in selected_ids if id.isdigit()]
        set_selected_ids(request, selected_ids)
        return redirect('checkout')

    # 3. Handle GET: retrieve selected IDs from session (if any)
    selected_ids = get_selected_ids(request)
    if not selected_ids:
        return redirect('cart')

        # 4. Filter order items that belong to this order
    # FIX: Use 'ordr' to get the orderitems_set
    selected_items = ordr.orderitems_set.filter(id__in=selected_ids).select_related('product')
    valid_ids = list(selected_items.values_list('id', flat=True))
    set_selected_ids(request, valid_ids)

    # 5. Calculate total for selected items
    total = sum(item.getitemtotal for item in selected_items)

    # 1. Fetch unique previous addresses
    # 1. Fetch unique previous addresses from the shippingaddress model
    previous_addresses = shippingaddress.objects.filter(customer=customer).values(
        'address', 'city', 'state', 'zipcode'
    ).distinct()

    # 2. Format them into a list of dictionaries
    addresses_list = []
    for idx, addr in enumerate(previous_addresses):
        addresses_list.append({
            "label": f"Address {idx + 1}",
            "street": addr['address'],  # Maps to the 'address' field in your model
            "city": addr['city'],  # Maps to the 'city' field
            "state": addr['state'],  # Maps to the 'state' field
            "zip": addr['zipcode']  # Maps to the 'zipcode' field
        })

    # 6. Prepare context
    context = {
        'selected_items': selected_items,
        'order_total': total,
        'addresses_json': json.dumps(addresses_list),
        'order': ordr,
        'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,
    }
    return render(request, 'store/checkout.html', context)
# adjusted imports



@login_required(login_url='/myauth/login')
@csrf_exempt
def create_checkout_session(request):
    if request.method != 'POST':
    # Fetch रिक्वेस्ट के लिए redirect की जगह JsonResponse भेजना चाहिए
        return JsonResponse({'error': 'Invalid request'}, status=400)
    customer = request.user.customer
    # 1. Find the most recent active cart
    ordr = order.objects.filter(customer=customer, complete=False).order_by('-id').first()
    # 2. If no active cart exists, create one
    if not ordr:
        ordr = order.objects.create(customer=customer, complete=False)
    # 1. Javascript (main.js) से भेजा गया JSON डेटा यहाँ पढ़ें
    try:
        data = json.loads(request.body)
        address = data.get('address', '')
        city = data.get('city', '')
        state = data.get('state', '')
        zipcode = data.get('zipcode', '')
        # एड्रेस को एक स्ट्रिंग में जोड़ें ताकि webhook में स्प्लिट (split) कर सकें
        full_address = f"{address}|{city}|{state}|{zipcode}"
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)
        # ==========================================
        # ADD THIS: Save the address to the database
        # ==========================================
    if address and city and state and zipcode:
            # We use get_or_create so we don't save duplicate addresses for the same order
        shippingaddress.objects.get_or_create(
            customer=customer,
            order=ordr,
            address=address,
            city=city,
            state=state,
            zipcode=zipcode
        )
        # ==========================================
    selected_ids = request.session.get("selected_item_ids", [])
    if not selected_ids:
        return JsonResponse({"error": "Cart is empty"}, status=400)

    selected_items = ordr.orderitems_set.filter(id__in=selected_ids)
    if not selected_items:
        return JsonResponse({"error": "Items not found"}, status=400)

    selected_items.update(checked=True)  # ✅ ADD THIS LINE

    line_items = []
    for item in selected_items:
        line_items.append({
            'price_data': {
                'currency': 'inr',
                'unit_amount': int(item.product.price * 100),
                'product_data': {
                    'name': item.product.title,
                    # ImageUrl को लिस्ट में तभी डालें जब वो मौजूद हो
                    # 'images': [item.product.ImageUrl.url] if item.product.ImageUrl else [],
                },
            },
            'quantity': item.quantity,
        })

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=request.build_absolute_uri(reverse('successview')) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.build_absolute_uri(reverse('checkout')),
            # 2. METADATA अपडेट करें: Webhook को cust और adr की ज़रूरत है!
            metadata={
                'order_id': ordr.id,
                'cust': customer.id,  # यह Webhook में काम आएगा
                'adr': full_address  # यह Webhook में एड्रेस सेव करेगा
            },
        )
        ordr.stripe_session_id = checkout_session.id
        ordr.save()

        return JsonResponse({"sessionId": checkout_session.id})

    except stripe.error.StripeError as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def reset_cart_count(customer_id, transaction_id):
    try:
        customer = Customer.objects.get(id=customer_id)
        # get current incomplete order (cart)
        ord = order.objects.get(customer=customer, complete=False)

        # get only checked items
        checked_items = ord.orderitems_set.filter(checked=True)

        for item in checked_items:
            item.transaction_id = transaction_id
            item.delete()
    except order.DoesNotExist:
        pass
def chatbot_view(request):
    return redirect('http://127.0.0.1:5000/')
def logout_view(request):
    logout(request)
    return redirect('/myauth/login')

def successview(request):
    session_id = request.GET.get('session_id')
    if not session_id:
        return render(request, 'store/cancelled.html', {
            'message': 'No session provided.'
        })
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception as e:
        return render(request, 'store/error.html', {
            'message': 'Invalid session.'
        })
    if session.payment_status != 'paid':
        return render(request, 'store/cancelled.html', {
            'message': 'Payment not completed.'
        })
    order_obj = order.objects.filter(stripe_session_id=session_id).first()
    if not order_obj:
        return render(request, 'store/cancelled.html', {'message': 'Order not found.'})
    customer_email = order_obj.customer.user.email
    if order_obj:
        # 3. ⭐ THE FIX: Extract the payment_intent and save it to transaction_id
        order_obj.transaction_id = session.payment_intent
        order_obj.complete = True
        order_obj.save()
        # ⭐ ADD THIS: Delete items that were left unchecked in the cart
        order_obj.orderitems_set.filter(checked=False).delete()
    # ✅ email FIRST (items still exist with checked=True)
    send_order_email(order_obj)
    # send_sms(order_obj)
    # make_phonecall(order_obj)
    # ✅ then reset the cart (this is the correct place)
    # try:
    #     reset_cart_count(order_obj.customer_id, order_obj.transaction_id)
    # except Exception as e:
    #     print("reset_cart_count failed:", e)
    return render(request, 'store/success.html', {
        'email': customer_email,
        'order_id': order_obj.id,
    })


@login_required
def cancel_order(request, order_id):
    if request.method == 'POST':
        # FIX 1: Query by 'customer__user' instead of 'user'
        ordr = get_object_or_404(order, id=order_id, customer__user=request.user)
        # 1. Check if we have a Stripe Transaction ID
        if not ordr.transaction_id or ordr.transaction_id == 'None':
            logger.warning(f"Order {ordr.id} has no Transaction ID. Cannot process Stripe refund.")
            # FIX 2: Use 'complete' not 'completed'
            # 4. Delete the order from the Django database
            ## order.delete()
            ordr.complete = False
            ordr.save()
            messages.error(request, "Order cancelled, but no Stripe transaction ID found. Please contact support.")
            return redirect('myorders')
        # 2. Process the Stripe Refund
        try:
            refund = stripe.Refund.create(
                payment_intent=ordr.transaction_id,
                reason='requested_by_customer'
            )
            logger.info(f"SUCCESS: Refunded Order {ordr.id}. Stripe Refund ID: {refund.id}")
            # FIX 2 (again): Use 'complete' not 'completed'
            ordr.complete = False
            ordr.save()
            messages.success(request, "Order successfully cancelled and refunded.")

        except stripe.error.InvalidRequestError as e:
            logger.error(f"Stripe InvalidRequestError for Order {ordr.id}: {str(e)}")
            messages.error(request, "Stripe could not process the refund. It may have already been refunded.")
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Error for Order {ordr.id}: {str(e)}")
            messages.error(request, "There was a network error with our payment processor. Please try again later.")
        except Exception as e:
            logger.error(f"System Error cancelling Order {ordr.id}: {str(e)}")
            messages.error(request, "An unexpected error occurred.")

        return redirect('myorders')

    return redirect('myorders')

def cancelled_view(request):
    return render(request,"store/cancelled.html")

@csrf_exempt
def stripe_webhook(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    endpoint_secret = settings.STRIPE_ENDPOINT_SECRE
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret,json.loads(payload), stripe.api_key
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
    print(event["type"])
    # Payment successful
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata=session.get("metadata",{})
        email = session['customer_details']['email']
        session_id = session['id']
        cid=metadata.get("cust")
        addr =metadata.get("adr")
        print(addr)
        customer=Customer.objects.get(id=cid)
        # current cart
        cart_order = order.objects.get(customer=customer, complete=False)
        # ordr,created=order.objects.get_or_create(customer=customer,complete=False)
        # checked items only
        checked_items = cart_order.orderitems_set.filter(checked=True)
        # create new completed order
        new_order = order.objects.create(
            customer=customer,
            complete=True,
            transaction_id=session.get('payment_intent')
        )
        # move checked items to new order
        for item in checked_items:
            item.order = new_order
            item.checked = False
            item.save()
            # shipping address
        ad, cty, sta, zipcode = addr.split("|")
        shippingaddress.objects.create(
            customer=customer,
            order=new_order,
            address=ad,
            city=cty,
            state=sta,
            zipcode=zipcode
        )
        print("Order created with checked items only")
        customer_id = session['metadata']['cust']
        order_obj = order.objects.get(stripe_session_id=session_id)
        # remove checked cart items
        reset_cart_count(customer_id, new_order.transaction_id)
        send_order_email(order_obj.customer.user.email, order_obj.id)

        print("Payment successful")
        print("Order created with checked items only")
    return HttpResponse(status=200)

def myorders(request):
    if not request.user.is_authenticated:
        return redirect('login') # Or wherever you want unauthenticated users to go

    # Check if the logged-in user is a Superuser
    if request.user.is_superuser:
        orders = order.objects.filter(complete=True).order_by('-date_created')
    else:
        # 2. Regular customers logic
        # norders = order.objects.filter(customer=customer, complete=True).order_by('-date_created')
        # Option B (if your custom manager already filters for the user):
        orders = order.objects.active_for_user(request.user).order_by('-date_created')
    # Calculate the grand total directly idatabase using your Python model method
    grand_total = sum(order.getordertotal for order in orders)
    context = {
        'orders': orders,
        'grand_total': grand_total
    }
    return render(request, 'store/myorders.html', context)

def product_details(request):
    """
    Product details page - mimics ASP.NET Core Details action
    """
    try:
        product = Product.objects.all()
    except Product.DoesNotExist:
        return render(request, '404.html', status=404)

    return render(request, 'store/product_details.html', {'products': product})

def config(request):
    return JsonResponse({
        "publicKey": settings.STRIPE_PUBLISHABLE_KEY
    })