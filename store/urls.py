from django.urls import path
from . import views
from .views import *

urlpatterns=[
    # path('', showprds, name="home"),
    path('', views.home, name='home'),
    path('editp/<int:pk>', views.edit_prodetails, name='edit_prodetails'),
    path('product_details/', views.product_details, name='details'),
    path('cart/',cart,name="cart"),
    path("checkout/", checkout, name="checkout"),
    path('chatbot/', views.chatbot_view, name='chatbot'),
    path("updatecart/", updatecart, name="updatecart"),
    path('myauth/logout/', views.logout_view, name='logout'),
    path('create-checkout-session/', views.create_checkout_session, name='create_checkout_session'),
    path('update-cart-ajax/', views.update_cart_ajax, name='update_cart_ajax'),
    path('payment-success/', views.successview, name='successview'),
    path('payment-cancel/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('myorders/cancelled/', views.cancelled_view, name='cancelled_order'),

    path('myorders/', views.myorders, name='myorders'),
    path("config/", views.config, name="config"),

]