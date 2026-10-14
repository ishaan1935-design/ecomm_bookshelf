# orders/services/sms_service.py
import html
from django.conf import settings
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse


# ---------------------------------------------------------------
# Shared helper — identical logic to email_service's checked_items
# ---------------------------------------------------------------
def _get_checked_items_and_total(order_obj):
    checked_items = list(
        order_obj.orderitems_set
        .filter(checked=True)
        .select_related("product")
    )

    items = []
    total = 0
    for item in checked_items:
        product_name = str(item.product.title)
        quantity = item.quantity
        price = item.product.price
        subtotal = price * quantity
        total += subtotal

        items.append({
            "name": product_name,
            "qty": quantity,
            "price": price,
            "subtotal": subtotal,
        })
    return items, total


# ---------------------------------------------------------------
# SMS
# ---------------------------------------------------------------
def send_sms(order_obj):
    sid = settings.TWILIO_ACCOUNT_SID
    token = settings.TWILIO_AUTH_TOKEN
    from_ = settings.TWILIO_PHONE_NUMBER

    if not (sid and token and from_):
        print("Twilio SMS creds missing — check .env")
        return None

    customer = order_obj.customer
    customer_name = customer.name or "Customer"
    to_phone = customer.phone  # must be E.164, e.g. +9198xxxxxxxx

    if not to_phone:
        print("Customer has no phone number — skipping SMS")
        return None

    items, total = _get_checked_items_and_total(order_obj)

    # Keep SMS body concise (Twilio max ~1600 chars; carriers segment anyway)
    lines = [
        f"Hi {customer_name},",
        f"Thanks for your order #{order_obj.id}!",
        "Items:",
    ]
    for it in items:
        lines.append(f"- {it['name']} x{it['qty']} = Rs.{it['subtotal']}")
    lines.append(f"Total: Rs.{total}")
    lines.append("We'll notify you when it ships. - Your Store")

    message = "\n".join(lines)

    try:
        client = Client(sid, token)
        resp = client.messages.create(
            body=message,
            from_=from_,
            to=to_phone,
        )
        print("Twilio SMS sent:", resp.sid)
        return resp
    except Exception as e:
        print("Twilio SMS error:", e)
        return None


# ---------------------------------------------------------------
# Phone call (text-to-speech via TwiML)
# ---------------------------------------------------------------
def make_phonecall(order_obj):
    sid = settings.TWILIO_ACCOUNT_SID
    token = settings.TWILIO_AUTH_TOKEN
    from_ = settings.TWILIO_PHONE_NUMBER

    if not (sid and token and from_):
        print("Twilio call creds missing — check .env")
        return None

    customer = order_obj.customer
    customer_name = customer.name or "Customer"
    to_phone = customer.phone

    if not to_phone:
        print("Customer has no phone number — skipping call")
        return None

    items, total = _get_checked_items_and_total(order_obj)

    # Build the spoken script
    response = VoiceResponse()
    response.say(
        f"Hello {customer_name}. Thank you for shopping with us. "
        f"Your order number {order_obj.id} has been placed successfully.",
        voice="Polly.Aditi",  # Indian English female voice
        language="en-IN",
    )

    response.say("Here are the items in your order:", voice="Polly.Aditi", language="en-IN")
    for it in items:
        response.say(
            f"{it['name']}, quantity {it['qty']}, subtotal {it['subtotal']} rupees.",
            voice="Polly.Aditi",
            language="en-IN",
        )

    response.say(
        f"Your total amount is {total} rupees. "
        f"Thank you and have a great day!",
        voice="Polly.Aditi",
        language="en-IN",
    )

    twiml = str(response)

    try:
        client = Client(sid, token)
        call = client.calls.create(
            twiml=twiml,
            from_=from_,
            to=to_phone,
        )
        print("Twilio call initiated:", call.sid)
        return call
    except Exception as e:
        print("Twilio call error:", e)
        return None
