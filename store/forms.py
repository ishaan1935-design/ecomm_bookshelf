from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import (
    Category, CoverType, Product, Customer,
    order, orderitems, shippingaddress
)


# User Registration Form (already exists)
class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


# Customer Form (already exists)
class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "phonenumber"]
        widgets = {
            'phonenumber': forms.TextInput(attrs={'placeholder': 'Enter phone number'}),
        }


# Category Form
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category name'}),
        }


# CoverType Form
class CoverTypeForm(forms.ModelForm):
    class Meta:
        model = CoverType
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cover type name'}),
        }


# Product Form
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'title', 'desc', 'price', 'author', 'isbn',
            'publication_year', 'category', 'cover_type',
            'digital', 'is_featured', 'is_bestseller',
            'stock_quantity', 'image'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Book title'}),
            'desc': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Description'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Price'}),
            'author': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Author name'}),
            'isbn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ISBN number'}),
            'publication_year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Year'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'cover_type': forms.Select(attrs={'class': 'form-control'}),
            'digital': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_bestseller': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Stock quantity'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

    # Custom validation for ISBN
    def clean_isbn(self):
        isbn = self.cleaned_data.get('isbn')
        if isbn and len(isbn) not in [10, 13]:
            raise forms.ValidationError("ISBN must be 10 or 13 characters long.")
        return isbn

    # Custom validation for price
    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price and price < 0:
            raise forms.ValidationError("Price cannot be negative.")
        return price


# Order Form (for admin updates)
class OrderForm(forms.ModelForm):
    class Meta:
        model = order
        fields = ['customer', 'complete', 'transaction_id', 'stripe_session_id']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'complete': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Transaction ID'}),
            'stripe_session_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Stripe Session ID'}),
        }

# Order Items Form
class OrderItemsForm(forms.ModelForm):
    class Meta:
        model = orderitems
        fields = ['order', 'product', 'quantity', 'checked', 'transaction_id']
        widgets = {
            'order': forms.Select(attrs={'class': 'form-control'}),
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'checked': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Transaction ID'}),
        }

    # Custom validation for quantity
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity < 0:
            raise forms.ValidationError("Quantity cannot be negative.")
        return quantity


# Shipping Address Form
class ShippingAddressForm(forms.ModelForm):
    class Meta:
        model = shippingaddress
        fields = ['customer', 'order', 'address', 'city', 'state', 'zipcode']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'order': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'zipcode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ZIP code'}),
        }

    # Custom validation for ZIP code
    def clean_zipcode(self):
        zipcode = self.cleaned_data.get('zipcode')
        if zipcode and not zipcode.isdigit():
            raise forms.ValidationError("ZIP code must contain only digits.")
        return zipcode


# Form for adding products to order (checkout)
class AddToCartForm(forms.Form):
    product_id = forms.IntegerField(widget=forms.HiddenInput())
    quantity = forms.IntegerField(
        min_value=1,
        max_value=99,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'style': 'width:70px;'})
    )


# Search Form (optional)
class SearchForm(forms.Form):
    query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search books...',
            'aria-label': 'Search'
        })
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-control'})
    )