from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone

# Custom User Model
class Customer(AbstractUser):
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    
    ROLES = (
        ('customer', 'Customer'),
        ('seller', 'Seller'),
        ('admin', 'Admin')
    )
    role = models.CharField(max_length=10, choices=ROLES)
    loyalty_points = models.IntegerField(default=0)

    groups = models.ManyToManyField(Group, related_name="custom_customer_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="custom_customer_permissions", blank=True)

    def __str__(self):
        return self.username

# Category Model
class Category(models.Model):
    category_name = models.CharField(max_length=255)
    parent_category = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self):
        return self.category_name  
# Product Model
class Product(models.Model):
    seller = models.ForeignKey(Customer, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField(max_length=1000, blank=True, null=True)  # Thay đổi từ ImageField sang URLField
    status = models.BooleanField(default=True)  # True: Còn hàng, False: Hết hàng
    def __str__(self):
        return self.product_name

# Promotion Model
class Promotion(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'Phần trăm'),
        ('amount', 'Số tiền cố định')
    ]
    promotion_code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, default='')  # Changed: added default=''
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    usage_limit = models.IntegerField(null=True, blank=True)
    usage_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'hoadeptrai_promotion'
        ordering = ['-created_at']

    def __str__(self):
        return self.promotion_code

    @property 
    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.usage_limit and self.usage_count >= self.usage_limit:
            return False
        return self.start_date <= now <= self.end_date

# Order Model
class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    ], default='pending')
    payment_method = models.CharField(max_length=20, choices=[
        ('cod', 'Cash on Delivery'),
        ('zalopay', 'ZaloPay'),
        ('bank', 'Bank Transfer')  # Add this line
    ], null=True, blank=True)
    payment_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ], default='pending')
    shipping_address = models.TextField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    zalopay_trans_id = models.CharField(max_length=100, null=True, blank=True)
    promotion = models.ForeignKey('Promotion', on_delete=models.SET_NULL, null=True, blank=True)
    complete = models.BooleanField(default=False)  # Add this field

    @property 
    def get_discount_amount(self):
        if not self.promotion:
            return 0
            
        subtotal = sum(item.get_total for item in self.orderitem_set.all())
        
        if self.promotion.discount_type == 'percent':
            discount = subtotal * (self.promotion.discount_value / 100)
            if self.promotion.max_discount_amount:
                discount = min(discount, self.promotion.max_discount_amount)
        else:
            discount = self.promotion.discount_value
            
        return discount

    @property
    def get_cart_total(self):
        subtotal = sum(item.get_total for item in self.orderitem_set.all())
        return subtotal - self.get_discount_amount

    @property
    def get_cart_items(self):
        return sum(item.quantity for item in self.orderitem_set.all())

    @property
    def is_complete(self):
        return self.status in ['delivered', 'cancelled']

    @property
    def is_cart(self):
        return self.status == 'pending'

# Order Item Model
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.quantity * self.price

    @property
    def get_total(self):
        return self.quantity * self.price

# Message Model
class Message(models.Model):
    sender = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='received_messages')
    message_text = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['sent_at']

# Favorite Model
class Favorite(models.Model):
    user = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    class Meta:
        unique_together = ('user', 'product')

# Notification Model
class Notification(models.Model):
    user = models.ForeignKey(Customer, on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)