import html
from django.core.mail import EmailMessage

from django.conf import settings
from ..models import order, orderitems
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

def send_email_brevo(order_obj):
    key = settings.BREVO_API_KEY
    print("DEBUG Brevo key len:", len(key) if key else None)

    if not key:
        print("Brevo key missing — check .env")
        return None
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = key

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )
    customer      = order_obj.customer
    customer_name = customer.name or "Customer"
    to_email      = customer.email
    # ✅ checked items only, eagerly evaluated
    checked_items = list(
        order_obj.orderitems_set
        .filter(checked=True)
        .select_related("product")
    )

    items_html = ""
    total      = 0
    for item in checked_items:
        product_name = html.escape(str(item.product.title))
        quantity     = item.quantity
        price        = item.product.price
        subtotal     = price * quantity
        total       += subtotal

        items_html += f"""
        <tr>
            <td style="padding:8px;">{product_name}</td>
            <td align="center" style="padding:8px;">{quantity}</td>
            <td align="right"  style="padding:8px;">₹ {price}</td>
            <td align="right"  style="padding:8px;">₹ {subtotal}</td>
        </tr>
        """
    customer_name = html.escape(str(customer_name))
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body>
        <h2>Hello {customer_name}, 👋</h2>
        <p>Thank you for shopping with us!</p>
        <p>Your order has been placed successfully and is now being processed.</p>

        <h3>Order #{order_obj.id}</h3>

        <table border="1" cellspacing="0" cellpadding="8" width="100%"
               style="border-collapse:collapse;">
            <tr style="background:#f2f2f2;">
                <th align="left">Product</th>
                <th align="center">Qty</th>
                <th align="right">Price</th>
                <th align="right">Subtotal</th>
            </tr>
            {items_html}
        </table>
        <br>
        <h3>Total Amount: ₹ {total}</h3>
        <p>Thank you for your order!</p>
    </body>
    </html>
    """

    sender = sib_api_v3_sdk.SendSmtpEmailSender(
        name=settings.BREVO_SENDER_NAME,
        email=settings.BREVO_SENDER_EMAIL
    )
    recipient = sib_api_v3_sdk.SendSmtpEmailTo(
        email=to_email,
        name=customer_name
    )
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        sender=sender,
        to=[recipient],
        subject=f"Order Confirmation #{order_obj.id}",
        html_content=html_content
    )

    try:
        response = api_instance.send_transac_email(send_smtp_email)
        print("Brevo email sent successfully:", response)
        return response
    except Exception as e:
        print("Brevo email error:", e)
        return None

def send_email_sendgrid(to_email, order_id):
    subject = "🧾 Order Confirmation!🎉 "
    # ✅ Get actual order instance
    order_obj = order.objects.get(id=order_id)

    # ✅ Get related items
    items = orderitems.objects.filter(order=order_obj)

    # ✅ Build item list
    items_text = ""
    for item in items:
        items_text += f"{item.product.name} (x{item.quantity})\n"
    message = f"""
Hi there 👋,
Thank you for shopping with us!


Your order has been successfully placed and is now being processed.
You have ordered:
🛍️ Order ID: {order_id}
You have ordered:
{items_text}
And the Total Order Amount: {order_obj.getcheckedtotal}

We will notify you once it is shipped 🚚

If you have any questions, feel free to reply to this email.

Best regards,
Your Store Team ❤️
"""

    email = EmailMessage(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [to_email],
    )

    email.send(fail_silently=False)