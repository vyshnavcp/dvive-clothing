from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.contrib.auth.models import User
from decimal import Decimal

class Contact(models.Model):
    name=models.CharField(max_length=20)
    email=models.CharField(max_length=200)
    phone=models.CharField(max_length=20)
    subject=models.CharField(max_length=400)
    message=models.CharField(max_length=200)
    
class Registration(models.Model):
    user_name=models.CharField(max_length=200)
    email=models.EmailField(max_length=80,unique=True)
    phone=models.CharField(max_length=20)
    authuser=models.ForeignKey(User,on_delete=models.CASCADE)
    def __str__(self):
        return self.user_name

class Article(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True, max_length=255)
    content = CKEditor5Field('Content', config_name='default')  
    image = models.ImageField(upload_to='articles/')
    posted_on = models.DateTimeField(auto_now_add=True)
    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    def __str__(self):
        return self.title
    
class TermsCondition(models.Model):
    content = CKEditor5Field('Content', config_name='default')
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return "Terms & Conditions"
    
class PrivacyPolicy(models.Model):
    content = CKEditor5Field('Content', config_name='default')
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return "Privacy Policy"

class FAQ(models.Model):
    question = models.CharField(max_length=300)
    answer = CKEditor5Field('Answer', config_name='default')
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.question
    
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    def __str__(self):
        return self.name
    
class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while SubCategory.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.name} → {self.name}"

class Product(models.Model):
    subcategory = models.ForeignKey('SubCategory',on_delete=models.CASCADE,related_name='products')
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=100)
    product_code = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()
    additional_info = models.JSONField(default=dict, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.BooleanField(default=True)
    is_signature_collection = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_best_seller = models.BooleanField(default=False)
    stock = models.PositiveIntegerField(default=0)
    image1 = models.ImageField(upload_to='products/', blank=True, null=True)
    image2 = models.ImageField(upload_to='products/', blank=True, null=True)
    image3 = models.ImageField(upload_to='products/', blank=True, null=True)
    image4 = models.ImageField(upload_to='products/', blank=True, null=True)
    image5 = models.ImageField(upload_to='products/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        if self.additional_info is None:
            self.additional_info = {}
        super().save(*args, **kwargs)
    def __str__(self):
        return self.name
    @property
    def style_type(self):
        return self.additional_info.get("style_type", [])
    @property
    def material_type(self):
        return self.additional_info.get("material_type", [])
    @property
    def profit(self):
        if self.cost_price is not None:
            return self.price - self.cost_price
        return None

class ProductColor(models.Model):
    product = models.ForeignKey(Product,on_delete=models.CASCADE,related_name='colors')
    name = models.CharField(max_length=50)      
    hex_code = models.CharField(max_length=7)   
    def __str__(self):
        return f"{self.product.name} - {self.name}"
    
class Size(models.Model):
    name = models.CharField(max_length=10)  
    order = models.PositiveIntegerField(default=0)
    def __str__(self):
        return self.name
    
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    size = models.ForeignKey(Size, on_delete=models.CASCADE,null=True, blank=True)
    color = models.ForeignKey(ProductColor, on_delete=models.CASCADE)
    stock = models.PositiveIntegerField(default=0)

class Review(models.Model):
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    message = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True) 
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'email'],
                name='unique_review_per_email_product'
            )
        ]
    def __str__(self):
        return f"{self.product} - {self.email}"
    
class Cart(models.Model):
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)
    coupon_code = models.CharField(max_length=50, blank=True, null=True)
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    def subtotal(self):
        return sum(item.total_price for item in self.items.all())
    def total(self):
        return max(self.subtotal() - self.coupon_discount, Decimal("0.00"))
    def update_totals(self):
        subtotal = self.subtotal()
        total = max(subtotal - self.coupon_discount, Decimal("0.00"))
        self.subtotal_amount = subtotal
        self.total_amount = total
        self.save(update_fields=["subtotal_amount", "total_amount"])
    def __str__(self):
        return self.registration.user_name


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    @property
    def total_price(self):
        return self.price * self.quantity
    def __str__(self):
        return f"{self.product.name} ({self.variant.color.name}-{self.variant.size.name})"
    
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True) 
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    active = models.BooleanField(default=True)
    min_cart_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    expiry_date = models.DateField(null=True, blank=True)
    def __str__(self):
        return self.code
    
class Order(models.Model):

    PAYMENT_CHOICES = (
        ("razorpay", "Razorpay"),
        ("cod", "Cash on Delivery"),
        ("pos", "POS Billing"),
    )

    POS_PAYMENT_CHOICES = (
        ("cash", "Cash"),
        ("upi", "UPI"),
        ("card", "Card"),
    )
    registration = models.ForeignKey("Registration", on_delete=models.CASCADE, null=True, blank=True)
    reference = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=50)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    town = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    land_mark = models.CharField(max_length=100, blank=True, null=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    coupon_code = models.CharField(max_length=50, blank=True, null=True)
    coupon_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        default="razorpay"
    )
    pos_payment_type = models.CharField(
        max_length=20,
        choices=POS_PAYMENT_CHOICES,
        blank=True,
        null=True,
        help_text="Only for POS Billing"
    )
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    refund_id = models.CharField(max_length=120, blank=True, null=True)
    refund_status = models.BooleanField(default=False)
    payment_status = models.BooleanField(default=False)

    is_completed = models.BooleanField(default=False)
    is_delivered = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)
    is_pos_order = models.BooleanField(default=False)
    cancel_requested = models.BooleanField(default=False)
    cancel_requested_at = models.DateTimeField(blank=True, null=True)

    refund_processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.is_pos_order and self.pos_payment_type:
            return f"Order #{self.id} - POS ({self.pos_payment_type})"
        return f"Order #{self.id} - {self.get_payment_method_display()}"

    @property
    def pos_payment_pending(self):
        return self.is_pos_order and not self.payment_status

    @property
    def fully_completed(self):
        if self.is_pos_order:
            return self.payment_status and self.is_completed
        return self.is_completed

    def get_status_display(self):
        if self.is_cancelled:
            return "Cancelled"
        if self.cancel_requested:
            return "Cancel Requested"
        if self.refund_processed:
            return "Refunded"
        if self.is_delivered:
            return "Delivered"
        if self.is_pos_order and not self.payment_status:
            return "POS Payment Pending"
        if not self.is_completed:
            return "Pending"
        return "Completed"
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    def total_price(self):
        return self.price * self.quantity
    
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    town = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    land_mark = models.CharField(max_length=100, blank=True)
    image = models.ImageField(upload_to="profile/", blank=True, null=True)
    def __str__(self):
        return self.user.first_name
        