from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Category(models.Model):
    """Model for book categories like Fiction, Non-Fiction, Science, etc."""
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
class CoverType(models.Model):
    """Model for book cover types like Hardcover, Paperback, etc."""
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
class Product(models.Model):
    """Model for books/products with category and cover type foreign keys."""
# Basic Information
    title = models.CharField(max_length=250)
    desc = models.TextField()
    price = models.FloatField()
    # Book Specific Fields
    author = models.CharField(max_length=200, blank=True, null=True)
    isbn = models.CharField(max_length=20, unique=True, blank=True, null=True)
    publication_year = models.IntegerField(blank=True, null=True)
    # Foreign Keys to Category and CoverType
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,  # Keep product if category is deleted
        null=True,
        blank=True,
        related_name='products'
    )
    cover_type = models.ForeignKey(
        CoverType,
        on_delete=models.SET_NULL,  # Keep product if cover type is deleted
        null=True,
        blank=True,
        related_name='products'
    )
    # Other Fields
    digital = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)
    stock_quantity = models.IntegerField(default=0)
    # Images
    image = models.ImageField(null=True, blank=True)

    @property
    def ImageUrl(self):
        try:
            return self.image.url
        except:
            return "/images/placeholder.png"
    def __str__(self):
        return self.title

class Customer(models.Model):
    name= models.CharField(max_length=250, null=True)
    email= models.CharField(max_length=250, null=True, unique=True)
    user= models.OneToOneField(User, on_delete=models.CASCADE)
    phonenumber = models.CharField(max_length=16,null=True,unique=True,blank=True)
    def __str__(self):
        return self.name

class OrderManager(models.Manager):
    # This is your reusable method!
    def active_for_user(self, user):
        # Returns only orders that are completed (completed=True) for the specific user
        return self.filter(customer__user=user, complete=True).order_by('-date_created')

class order(models.Model):
    customer=models.ForeignKey(Customer,on_delete=models.CASCADE)
    date_created=models.DateTimeField(auto_now_add=True)
    complete=models.BooleanField(default=False)
    stripe_session_id = models.CharField(max_length=275, blank=True, null=True)
    transaction_id=models.CharField(max_length=500,null=True, blank=True)
    objects = OrderManager()
    def __str__(self):
        return f"Order {self.id}"
    @property
    def getcheckedqty(self):
        return sum([item.quantity for item in self.orderitems_set.filter(checked=True)])
    @property
    def getcheckedtotal(self):
        return sum([item.getitemtotal for item in self.orderitems_set.filter(checked=True)])
    @property
    def getordertotal(self): # Only sum the items that were actually purchased
        return sum(item.getitemtotal for item in self.orderitems_set.filter(checked=True))

class orderitems(models.Model):
    order=models.ForeignKey(order,on_delete=models.CASCADE)
    product=models.ForeignKey(Product,on_delete=models.CASCADE)
    quantity=models.IntegerField(default=0)
    checked = models.BooleanField(default=False)  # NEW FIELD
    transaction_id=models.CharField(max_length=500,null=True, blank=True)
    class Meta:
        unique_together = ('order', 'product')
    @property
    def getitemtotal(self):
        return self.quantity*self.product.price

class shippingaddress(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    order = models.ForeignKey(order, on_delete=models.CASCADE)
    city = models.CharField(max_length=500)
    state = models.CharField(max_length=500)
    address= models.CharField(max_length=500)
    zipcode = models.CharField(max_length=50)
    def __str__(self):
        return self.address