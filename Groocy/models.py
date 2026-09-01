# models.py
from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True) # Used for filtering

    def save(self, *args, **kwargs):
        # Always store the name in a consistent format (e.g., Title Case)
        # This way "drinks", "DRINKS", and "drINks" all become "Drinks"
        self.name = self.name.strip().title()
        self.slug = self.name.lower().replace(" ", "-")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    price = models.PositiveIntegerField() # Store in Kobo/Cents for Paystack
    image = models.ImageField(upload_to='products/')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    # Tracks exact quantity
    instock = models.PositiveIntegerField(default=0)
    UNIT_CHOICES = [
        ('Piece', 'Piece'),
        ('Pack', 'Pack'),
        ('Carton', 'Carton'),
    ]
    unit_type = models.CharField(max_length=20, choices=UNIT_CHOICES, default='Piece')
    
    @property
    def is_in_stock(self):
        return self.instock > 0

    def __str__(self):
        # Visually differentiate in Django Admin / DB queries
        if self.unit_type != 'Piece':
            return f"{self.name} ({self.unit_type})"
        return self.name

class Order(models.Model):
    STATUS_CHOICES = [
        ('Ready', 'Ready for Pickup'),
        ('Accepted', 'Order Accepted'),
        ('Packing', 'Packing Order'),
        ('Transit', 'In Transit'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
        ('Timeout', 'Timeout'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    courier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')
    amount = models.PositiveIntegerField()
    shipping_fee = models.PositiveIntegerField(default=0)
    ref = models.CharField(max_length=200, unique=True)
    verified = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=10, default='Online')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Accepted')
    
    # Timestamps for each stage
    accepted_at = models.DateTimeField(null=True, blank=True)
    packing_at = models.DateTimeField(null=True, blank=True)
    transit_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    address = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    # Crucial for cancelled order on Courier's end: tracking the last modification
    updated_at = models.DateTimeField(auto_now=True)

    CANCEL_CHOICES = [
        ('Customer', 'Customer'),
        ('Courier', 'Courier'),
    ]
    cancelled_by = models.CharField(max_length=10, choices=CANCEL_CHOICES, blank=True, null=True)
    
    
class OrderItem(models.Model):
    UNIT_CHOICES = (
        ('piece', 'Piece'),
        ('pack', 'Pack'),
        ('carton', 'Carton'),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_name = models.CharField(max_length=255)
    product_image = models.CharField(max_length=500, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    unit_type = models.CharField(max_length=10, choices=UNIT_CHOICES, default='piece')

    def get_total_item_price(self):
        return self.price * self.quantity


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    address = models.CharField(max_length=255, blank=True, null=True)

    def __cl__str__(self):
        return f"{self.user.username}'s Profile"
        

class DeliveryRating(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    rating_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class CourierProfile(models.Model):
    HALL_CHOICES = [
        ('John Hall', 'John Hall'),
        ('Paul Hall', 'Paul Hall'),
        ('Mary Hall', 'Mary Hall'),
        ('Lydia Hall', 'Lydia Hall'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='courier_profile')
    location_1 = models.CharField(max_length=50, choices=HALL_CHOICES)
    location_2 = models.CharField(max_length=50, choices=HALL_CHOICES, blank=True, null=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_available = models.BooleanField(default=True)
    # Added for soft-delete capabilities
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username 
    


