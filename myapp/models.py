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
    password=models.CharField(max_length=25)
    authuser=models.ForeignKey(User,on_delete=models.CASCADE)
    def __str__(self):
        return self.user_name


class Article(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True, max_length=255)
    content = models.TextField()
    image = models.ImageField(upload_to='articles/')
    posted_on = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Always regenerate slug when saving
        self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
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
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='subcategories'
    )
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
    # Relations
    subcategory = models.ForeignKey('SubCategory',on_delete=models.CASCADE,related_name='products')

    # Basic Product Details
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=100)
    product_code = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)

    # Content
    description = models.TextField()
    additional_info = models.JSONField(default=dict, blank=True)

    # Price
    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    # Flags
    status = models.BooleanField(default=True)
    is_signature_collection = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_best_seller = models.BooleanField(default=False)

    # Stock
    stock = models.PositiveIntegerField(default=0)

    # Sizes
    sizes = models.ManyToManyField('Size', blank=True)

    # Images
    image1 = models.ImageField(upload_to='products/', blank=True, null=True)
    image2 = models.ImageField(upload_to='products/', blank=True, null=True)
    image3 = models.ImageField(upload_to='products/', blank=True, null=True)
    image4 = models.ImageField(upload_to='products/', blank=True, null=True)
    image5 = models.ImageField(upload_to='products/', blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Auto slug
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



class ProductColor(models.Model):
    product = models.ForeignKey(Product,on_delete=models.CASCADE,related_name='colors')
    name = models.CharField(max_length=50)      # e.g. Yellow
    hex_code = models.CharField(max_length=7)   # e.g. #F2C94C

    def __str__(self):
        return f"{self.product.name} - {self.name}"
class Size(models.Model):
    name = models.CharField(max_length=10)  # S, M, L, XL
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name
class Review(models.Model):
    registration=models.ForeignKey(Registration,on_delete=models.CASCADE)
    product=models.ForeignKey(Product,on_delete=models.CASCADE)
    name=models.CharField(max_length=200)
    email=models.CharField(max_length=200)
    rating = models.PositiveSmallIntegerField(
    validators=[MinValueValidator(1), MaxValueValidator(5)]) 
    message=models.CharField(max_length=200)


class Cart(models.Model):
    registration = models.ForeignKey(
        Registration,
        on_delete=models.CASCADE,
        related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Coupon fields
    coupon_code = models.CharField(max_length=50, blank=True, null=True)
    coupon_discount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )


    subtotal_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )

 
    def subtotal(self):
        return sum(item.total_price() for item in self.items.all())

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
    cart = models.ForeignKey(Cart,related_name="items",on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    color = models.ForeignKey(ProductColor, on_delete=models.SET_NULL, null=True)
    size = models.ForeignKey(Size, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def total_price(self):
        return self.price * self.quantity


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)  # e.g., DISCOUNT50
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
    )

    registration = models.ForeignKey(Registration, on_delete=models.CASCADE)

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
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )

    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_CHOICES, default="razorpay"
    )

    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)

    payment_status = models.BooleanField(default=False)   # Payment success

    is_completed = models.BooleanField(default=False)     # Admin completed

    # ✅ ADD THIS ONLY
    is_delivered = models.BooleanField(default=False)     # Delivery status
    is_cancelled = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.payment_method}"



class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    color = models.ForeignKey(ProductColor, on_delete=models.SET_NULL, null=True)
    size = models.ForeignKey(Size, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def total_price(self):
        return self.price * self.quantity
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    image = models.ImageField(upload_to='profile_images/', blank=True, null=True)

    def __str__(self):
        return self.user.first_name