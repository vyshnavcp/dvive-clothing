from datetime import date, datetime
import json
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from .models import *
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.contrib import messages
from django.contrib.auth.models import User,Group
from django.contrib.auth import authenticate,login,logout
from django.db.models import Q, Count
from django.contrib.auth.decorators import login_required,user_passes_test
import razorpay
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
from django.utils.text import slugify
from django.db.models import Sum
from django.utils.timezone import now
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import F, Avg, Count
from django.template.loader import render_to_string
from django.db import IntegrityError
from .forms import FAQForm, PrivacyForm,TermsForm
import re
import json
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from django.utils.dateparse import parse_date 
from django.views.decorators.http import require_POST
from .forms import ArticleForm, TermsForm
from django.db import transaction
from django.conf import settings
from django.urls import reverse
from django.db.models import F
from .decorators import role_required
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
import logging
from django.utils.html import escape
from datetime import timedelta
from django.middleware.csrf import rotate_token

def home(request):
   blogs = Article.objects.order_by('-posted_on')[:4]
   best_seller_products = Product.objects.filter(is_best_seller=True)[:5]
   featured_product= Product.objects.filter(is_featured=True)[:5]
   signature_products = Product.objects.filter( is_signature_collection=True,status=True)[:8]
   categories = Category.objects.prefetch_related("subcategories").all()
   banners = HomeBanner.objects.filter(is_active=True)
   return render(request, "home.html", {'blogs': blogs,
   'best_seller_products': best_seller_products,'featured_product':featured_product,
   'signature_products': signature_products,"categories": categories,'banners': banners})

def about(request):
    return render(request, "about.html")

def blog(request):
    blogs_list = Article.objects.all().order_by('-posted_on')
    paginator = Paginator(blogs_list, 4) 
    page_number = request.GET.get('page')
    blogs = paginator.get_page(page_number)
    return render(request, 'blog.html', {'blogs': blogs})

def blog_detail(request, slug):
    blog_detail = get_object_or_404(Article, slug=slug)
    return render(request, 'blog_detail.html', {'blog': blog_detail})

def contact(request):
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('comment', '').strip()
        if not name:
            return JsonResponse({"status": "error", "message": "Name is required"})
        if len(name) < 3:
            return JsonResponse({"status": "error", "message": "Name must be at least 3 characters"})
        if not re.match(r'^[A-Za-z ]+$', name):
            return JsonResponse({"status": "error", "message": "Name must contain only letters"})
        email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not email:
            return JsonResponse({"status": "error", "message": "Email is required"})
        if not re.match(email_regex, email):
            return JsonResponse({"status": "error", "message": "Enter a valid email address"})
        if not phone:
            return JsonResponse({"status": "error", "message": "Phone number is required"})
        if not phone.isdigit():
            return JsonResponse({"status": "error", "message": "Phone must contain only numbers"})
        if len(phone) != 10:
            return JsonResponse({"status": "error", "message": "Phone must be exactly 10 digits"})
        if not message:
            return JsonResponse({"status": "error", "message": "Message cannot be empty"})
        Contact.objects.create(
            name=name,
            email=email,
            phone=phone,
            subject=subject,
            message=message,
        )
        return JsonResponse({
            "status": "success",
            "message": "Message sent successfully!"
        })
    return render(request, "contact.html")


def product(request, slug=None):
    products = Product.objects.filter(status=True).distinct()
    query = request.GET.get('q')
    if query:
        products = products.filter(name__icontains=query)
    subcategory_counts = SubCategory.objects.annotate(
        product_count=Count('products', distinct=True)
    )
    size_counts = Size.objects.annotate(
        product_count=Count('productvariant__product', distinct=True)
    )
    if slug:
        if Category.objects.filter(slug=slug).exists():
            products = products.filter(subcategory__category__slug=slug)
            pagination_base = reverse('filter_by_category', args=[slug])
        else:
            products = products.filter(subcategory__slug=slug)
            pagination_base = reverse('filter_by_subcategory', args=[slug])

        active_slug = slug
    else:
        pagination_base = reverse('product')
        active_slug = None
    size_filter = request.GET.get('size')

    if size_filter:
        products = products.filter(
            variants__size__name=size_filter
        ).distinct()
    if request.GET.get('signature') == '1':
        products = products.filter(
            is_signature_collection=True
        )
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'product.html', {
        'page_obj': page_obj,
        'subcategory_counts': subcategory_counts,
        'size_counts': size_counts,
        'pagination_base': pagination_base,
        'active_slug': active_slug,
        'active_size': size_filter,
        'search_query': query,
    })

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    variants = product.variants.select_related('size', 'color')
    colors = list({v.color for v in variants if v.color})
    sizes = list({v.size for v in variants if v.size})
    reviews = Review.objects.filter(product=product).order_by('-id')
    first_three_reviews = reviews[:3]
    remaining_reviews = reviews[3:]
    average_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    total_reviews = reviews.count()
    rating_counts = reviews.values('rating').annotate(count=Count('rating'))
    rating_dict = {i: 0 for i in range(1, 6)}
    for item in rating_counts:
        rating_dict[item['rating']] = item['count']
    rating_percent = {}
    for i in range(1, 6):
        rating_percent[i] = round((rating_dict[i] / total_reviews) * 100) if total_reviews else 0
    related_products = Product.objects.filter(
        subcategory=product.subcategory
    ).exclude(id=product.id)[:4]
    product_images = []
    for img_field in ['image1', 'image2', 'image3', 'image4', 'image5']:
        img = getattr(product, img_field)
        if img:
            product_images.append(img.url)
    variant_stock = {}
    for v in variants:
        if v.color_id and v.size_id:
            key = f"{v.color_id}-{v.size_id}"
        elif v.color_id and not v.size_id:
            key = f"{v.color_id}"
        elif v.size_id and not v.color_id:
            key = f"size-{v.size_id}"
        else:
            key = "default"
        variant_stock[key] = v.stock 
    return render(request, 'product_detail.html', {
        'product': product,
        'colors': colors,
        'sizes': sizes,
        'reviews': reviews,
        'first_three_reviews': first_three_reviews,
        'remaining_reviews': remaining_reviews,
        'average_rating': round(average_rating, 1),
        'total_reviews': total_reviews,
        'rating_percent': rating_percent,
        'related_products': related_products,
        'product_images': product_images,
        'variant_stock': variant_stock,
    })

def add_to_cart(request, product_id):
    if not request.user.is_authenticated:
        return JsonResponse({
            "success": False,
            "message": "Please login to add items to your cart."
        })
    product = get_object_or_404(Product, id=product_id)

    size_id = request.POST.get("size")
    color_id = request.POST.get("color")

    try:
        quantity = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        quantity = 1

    if quantity < 1:
        quantity = 1

    if color_id and size_id:
        variant = product.variants.filter(color_id=color_id, size_id=size_id).first()

    elif color_id and not size_id:
        variant = product.variants.filter(color_id=color_id, size__isnull=True).first()

    elif size_id and not color_id:
        variant = product.variants.filter(size_id=size_id, color__isnull=True).first()

    else:
  
        variant = product.variants.filter(color__isnull=True, size__isnull=True).first()
    
    
    variant = product.variants.filter(
        size_id=size_id,
        color_id=color_id
    ).first()
    if not variant:
        return JsonResponse({
            "success": False,
            "message": "Invalid size/color combination."
        })
    if variant.stock <= 0:
        return JsonResponse({
            "success": False,
            "message": "This variant is out of stock."
        })
    if quantity > variant.stock:
        return JsonResponse({
            "success": False,
            "message": f"Only {variant.stock} item(s) available."
        })

    registration = get_object_or_404(Registration, authuser=request.user)
    cart, _ = Cart.objects.get_or_create(registration=registration)

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        variant=variant,
        defaults={
            "quantity": quantity,
            "price": product.price  
        }
    )
    if not created:
        new_quantity = item.quantity + quantity

        if new_quantity > variant.stock:
            return JsonResponse({
                "success": False,
                "message": f"Only {variant.stock} item(s) available."
            })

        item.quantity = new_quantity
        item.save()
    cart_count = cart.items.count()
    return JsonResponse({
        "success": True,
        "message": "Product added to cart!",
        "cart_count": cart_count
    })

@login_required
@require_POST
def delete_review(request, id):
    review = get_object_or_404(Review, id=id)
    if review.email != request.user.email and not request.user.is_staff:
        return JsonResponse({
            "status": "error",
            "message": "Not allowed"
        })
    review.delete()
    return JsonResponse({
        "status": "success"
    })

def register(request):
    return render(request,'register.html')
def reg_post(request):
    name = request.POST['name']
    email = request.POST['email']
    password = request.POST['password']
    confirm_password = request.POST.get('confirm_password', '').strip()
    phone = request.POST['phone']

    # ✅ CHECK FIRST (IMPORTANT)
    if password != confirm_password:
        messages.error(request, "Passwords do not match")
        return redirect('register')

    # (optional safety)
    if User.objects.filter(username=email).exists():
        messages.error(request, "Email already exists")
        return redirect('register')

    # ✅ CREATE USER AFTER VALIDATION
    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=name
    )

    gp = Group.objects.get(name='registration')
    user.groups.add(gp)
    user.save()

    send_mail(
        subject="Account Created Successfully",
        message=(
            "Dear Customer,\n\n"
            "Welcome to our eCommerce platform!\n\n"
            "Your account has been created successfully and you can now start shopping with us.\n\n"
            "Use your registered email address to log in and explore our wide range of products.\n\n"
            "If you need any assistance, feel free to contact our support team.\n\n"
            "Happy Shopping!\n"
            "Regards,\n"
            "eCommerce Support Team"
        ),
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
    )

    Registration.objects.create(
        user_name=name,
        email=email,
        phone=phone,
        authuser=user
    )

    messages.success(request, "Account created successfully. Please login.")
    return redirect('user_login')

def ajax_validate_register(request):
    email = request.GET.get('email', '').strip()
    phone = request.GET.get('phone', '').strip()
    password = request.GET.get('password', '').strip()
    confirm_password = request.GET.get('confirm_password', '').strip()  # ✅ ADD
    name = request.GET.get('name', '').strip()

    data = {
        'email_error': '',
        'phone_error': '',
        'password_error': '',
        'confirm_password_error': '',  # ✅ ADD
        'name_error': '',
    }

    # ✅ NAME
    if name:
        if len(name) < 3:
            data['name_error'] = 'Name must be at least 3 characters'
        elif not re.match(r'^[A-Za-z ]+$', name):
            data['name_error'] = 'Name must contain only letters and spaces'

    # ✅ EMAIL
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if email:
        if not re.match(email_regex, email):
            data['email_error'] = 'Enter a valid email address'
        elif User.objects.filter(username=email).exists():
            data['email_error'] = 'Email already exists'

    # ✅ PHONE
    if phone:
        if not phone.isdigit():
            data['phone_error'] = 'Phone must contain only numbers'
        elif len(phone) != 10:
            data['phone_error'] = 'Phone must be exactly 10 digits'
        elif Registration.objects.filter(phone=phone).exists():
            data['phone_error'] = 'Phone number already registered'

    # ✅ PASSWORD
    if password:
        if len(password) < 8:
            data['password_error'] = 'Minimum 8 characters required'
        elif not re.search(r'[A-Z]', password):
            data['password_error'] = 'Must contain at least 1 uppercase letter'
        elif not re.search(r'[0-9]', password):
            data['password_error'] = 'Must contain at least 1 number'
        elif not re.search(r'[!@#$%^&*]', password):
            data['password_error'] = 'Must contain at least 1 special character (!@#$%^&*)'

    # ✅ CONFIRM PASSWORD (NEW)
    if confirm_password:
        if confirm_password != password:
            data['confirm_password_error'] = 'Passwords do not match'

    return JsonResponse(data)

def staff_required(user):
    return user.is_staff

def user_login(request):
    return render(request,'login.html')

def login_post(request):
    login_input = request.POST.get('name','').strip()
    password = request.POST.get('password','').strip()

    if not login_input:
        messages.error(request,"Username or Email required")
        return redirect('user_login')

    if not password:
        messages.error(request,"Password required")
        return redirect('user_login')

    try:
        user_obj = User.objects.get(email__iexact=login_input)
        username = user_obj.username
    except User.DoesNotExist:
        username = login_input

    user = authenticate(request, username=username, password=password)

    if user:
        login(request, user)
        rotate_token(request)

        # ✅ ADD THIS HERE (clear old messages)
        from django.contrib.messages import get_messages
        storage = get_messages(request)
        for _ in storage:
            pass

        messages.success(request, f"Welcome back, {user.username}")

        if user.is_superuser:
            return redirect("dashboard")
        if user.groups.filter(name="Accountant").exists():
            return redirect("dashboard")
        if user.groups.filter(name="Staff").exists():
            return redirect("dashboard")

        return redirect("home")

    messages.error(request,"Invalid username or password")
    return redirect('user_login')
    
def user_logout(request):
    storage = messages.get_messages(request)
    for _ in storage:
        pass

    logout(request)
    return redirect("user_login")

@login_required
def review_post(request, slug):
    if request.method == 'POST':
        user = request.user
        product = get_object_or_404(Product, slug=slug)
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        if not rating:
            return JsonResponse({
                'status': 'error',
                'message': '⚠ Please select a rating.'
            })
        if not comment:
            return JsonResponse({
                'status': 'error',
                'message': '⚠ Please write a review.'
            })
        registration, created = Registration.objects.get_or_create(authuser=user)
        try:
            Review.objects.create(
                registration=registration,
                product=product,
                name=user.get_full_name() if user.get_full_name() else user.username,
                email=user.email,
                rating=int(rating),
                message=comment
            )
        except IntegrityError:
            return JsonResponse({
                'status': 'error',
                'message': '⚠ You have already submitted a review for this product.'
            })
        return JsonResponse({
            'status': 'success',
            'message': '✅ Thank you for your review!'
        })
    return JsonResponse({
        'status': 'error',
        'message': '⚠ Invalid request method.'
    })

@login_required(login_url='user_login')
def cart_page(request):
    if request.user.is_staff:
        return redirect("home")

    try:
        registration = Registration.objects.get(authuser=request.user)
    except Registration.DoesNotExist:
        messages.warning(request, "Only customers can access cart.")
        return redirect("home")

    cart, _ = Cart.objects.get_or_create(registration=registration)
    items = cart.items.all()
    has_items = items.exists()
    message = None

    if request.method == "POST" and has_items:
        if "remove_coupon" in request.POST:
            cart.coupon_code = None
            cart.coupon_discount = Decimal("0.00")
            cart.save()
            message = "Coupon removed"

        elif "coupon_code" in request.POST:
            coupon_code = request.POST.get("coupon_code", "").strip()

            if coupon_code:
                try:
                    coupon = Coupon.objects.get(
                        code__iexact=coupon_code,
                        active=True
                    )

                    if coupon.expiry_date and coupon.expiry_date < date.today():
                        cart.coupon_code = None
                        cart.coupon_discount = Decimal("0.00")
                        message = "Coupon expired"

                    else:
                        # ✅ FIX 1: prevent negative discount
                        subtotal = cart.subtotal()
                        discount = min(coupon.discount_amount, subtotal)

                        cart.coupon_code = coupon.code
                        cart.coupon_discount = discount
                        message = "Coupon applied!"

                except Coupon.DoesNotExist:
                    cart.coupon_code = None
                    cart.coupon_discount = Decimal("0.00")
                    message = "Invalid coupon"

                cart.save()

    # =====================================================
    # ✅ FIX 2: AUTO VALIDATE COUPON EVERY PAGE LOAD
    # =====================================================
    if cart.coupon_code:
        try:
            coupon = Coupon.objects.get(
                code__iexact=cart.coupon_code,
                active=True)

        # ❌ expired
            if coupon.expiry_date and coupon.expiry_date < date.today():
                cart.coupon_code = None
                cart.coupon_discount = Decimal("0.00")
                message = "Coupon expired and removed"

            else:
                subtotal = cart.subtotal()
                cart.coupon_discount = min(coupon.discount_amount, subtotal)

        except Coupon.DoesNotExist:
        # ❌ deleted by admin / inactive
            cart.coupon_code = None
            cart.coupon_discount = Decimal("0.00")
            message = "Coupon is no longer available and removed"

        cart.save()

    cart.update_totals()

    return render(request, "cart.html", {
        "cart": cart,
        "items": items,
        "has_items": has_items,
        "subtotal": cart.subtotal(),
        "total": cart.total(),
        "db_subtotal": cart.subtotal_amount,
        "db_total": cart.total_amount,
        "coupon_discount": cart.coupon_discount,
        "coupon_code": cart.coupon_code,
        "message": message,
    })
@login_required
def change_cart_quantity(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    cart = item.cart
    if request.POST.get("action") == "plus":
        if item.quantity < item.product.stock:
            item.quantity += 1
    elif request.POST.get("action") == "minus":
        if item.quantity > 1:
            item.quantity -= 1
    item.save()
    cart.update_totals()

    return redirect("cart_page")

@login_required
def update_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "plus":
            item.quantity += 1
        elif action == "minus" and item.quantity > 1:
            item.quantity -= 1
        item.save()
    return redirect("cart_page")

@login_required
def remove_cart_item(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    item.delete()
    return redirect("cart_page")

@login_required
def empty_cart(request):
    registration = get_object_or_404(Registration, authuser=request.user)
    cart = Cart.objects.filter(registration=registration).first()
    if cart:
        cart.items.all().delete()
        cart.coupon_code = None
        cart.coupon_discount = Decimal("0.00")
        cart.save()
    return redirect("cart_page")

@login_required
def checkout(request):
    registration = get_object_or_404(Registration, authuser=request.user)
    cart = get_object_or_404(Cart, registration=registration)
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    items = cart.items.select_related("product", "variant")
    if not items.exists():
        messages.warning(request, "Your cart is empty")
        return redirect("cart_page")
    return render(request, "checkout.html", {
        "cart": cart,
        "items": items,
        "subtotal": cart.subtotal(),
        "total": cart.total(),
        "coupon_discount": cart.coupon_discount,
        "profile_address": profile.address,
        "profile_phone": profile.phone,
        "profile_town": profile.town,
        "profile_state": profile.state,
        "profile_pincode": profile.pincode,
        "profile_land_mark": profile.land_mark,
    })

def calculate_shipping(subtotal):
    if subtotal < Decimal("799.00"):
        return Decimal("80.00")
    return Decimal("0.00")

@login_required
def checkout_post(request):
    if request.method != "POST":
        return redirect("home")

    registration = get_object_or_404(Registration, authuser=request.user)
    cart = get_object_or_404(Cart, registration=registration)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    items = cart.items.select_related("product", "variant")

    if not items.exists():
        messages.warning(request, "Your cart is empty")
        return redirect("cart_page")

    # Form data
    first_name = request.POST.get("first_name")
    email = request.POST.get("email")
    phone = request.POST.get("phone")
    address = request.POST.get("address")
    town = request.POST.get("town")
    state = request.POST.get("state")
    pincode = request.POST.get("pincode")
    land_mark = request.POST.get("land_mark")
    payment_method = request.POST.get("payment-option")

    if not request.POST.get("terms_condition"):
        messages.error(request, "Accept terms & conditions")
        return redirect("checkout")

    # Save profile
    profile.address = address
    profile.phone = phone
    profile.town = town
    profile.state = state
    profile.pincode = pincode
    profile.land_mark = land_mark
    profile.save()

    # Stock check
    for item in items:
        if item.quantity > item.variant.stock:
            messages.error(request, f"{item.product.name} only {item.variant.stock} available")
            return redirect("cart_page")

    # ✅ SHIPPING CALCULATION
    subtotal = cart.subtotal()
    shipping = calculate_shipping(subtotal)
    total = subtotal - cart.coupon_discount + shipping

    # ================= COD =================
    if payment_method == "cod":
        from django.db import transaction

        with transaction.atomic():
            order = Order.objects.create(
                registration=registration,
                first_name=first_name,
                email=email,
                phone=phone,
                address=address,
                town=town,
                state=state,
                pincode=pincode,
                land_mark=land_mark,
                subtotal=subtotal,
                total=total,
                coupon_code=cart.coupon_code,
                coupon_discount=cart.coupon_discount,
                payment_method="cod",
                payment_status=False
            )

            for item in items:
                variant = item.variant
                variant.stock -= item.quantity
                variant.save()

                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    variant=variant,
                    quantity=item.quantity,
                    price=item.price
                )

            cart.items.all().delete()
            cart.coupon_code = None
            cart.coupon_discount = Decimal("0.00")
            cart.save()

        return redirect("cash_on_delivery_success", order_id=order.id)

    # ================= RAZORPAY =================
    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    amount = int(total * 100)  # ✅ includes shipping

    razorpay_order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": "1"
    })

    # Save session
    request.session["checkout_data"] = {
        "first_name": first_name,
        "email": email,
        "phone": phone,
        "address": address,
        "town": town,
        "state": state,
        "pincode": pincode,
        "land_mark": land_mark,
        "cart_id": cart.id,
        "registration_id": registration.id,
    }

    return render(request, "checkout_payment.html", {
        "razorpay_order_id": razorpay_order["id"],
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "amount": amount,
        "display_amount": total,  # ✅ includes shipping
        "checkout_data": request.session["checkout_data"]
    })

@login_required
def cash_on_delivery_success(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        registration__authuser=request.user,
        payment_method="cod"
    )
    return render(request, "cash_on_delivery_success.html", {"order": order})

@login_required
def ajax_validate_checkout(request):
    phone = request.GET.get("phone", "").strip()
    pincode = request.GET.get("pincode", "").strip()
    town = request.GET.get("town", "").strip()
    address = request.GET.get("address", "").strip()
    state = request.GET.get("state", "").strip()
    land_mark = request.GET.get("land_mark", "").strip()
    data = {
        "phone_error": "",
        "pincode_error": "",
        "town_error": "",
        "address_error": "",
        "state_error": "",
        "land_mark_error": "",
    }
    if phone:
        if not phone.isdigit():
            data["phone_error"] = "Phone must contain only numbers"
        elif len(phone) != 10:
            data["phone_error"] = "Phone must be 10 digits"
    if pincode:
        if not pincode.isdigit():
            data["pincode_error"] = "Pincode must contain only numbers"
        elif len(pincode) != 6:
            data["pincode_error"] = "Pincode must be 6 digits"
    if state in ["", "Select a state"]:
        data["state_error"] = "Please select a valid state"
    if town and len(town) < 2:
        data["town_error"] = "Enter a valid town/city"
    if address and len(address) < 10:
        data["address_error"] = "Address is too short"
    if land_mark and len(land_mark) < 3:
        data["land_mark_error"] = "Landmark must be at least 3 characters"

    return JsonResponse(data)

def ajax_shipping_charge(request):
    registration = get_object_or_404(Registration, authuser=request.user)
    cart = get_object_or_404(Cart, registration=registration)
    subtotal = cart.subtotal()
    if subtotal < Decimal("899.00"):
        shipping = Decimal("80.00")
    else:
        shipping = Decimal("0.00")
    total = subtotal - cart.coupon_discount + shipping
    return JsonResponse({
        "shipping": float(shipping),
        "subtotal": float(subtotal),
        "total": float(total)
    })


@csrf_exempt
@transaction.atomic
def payment_success_post(request):
    if request.method != "POST":
        return JsonResponse({"success": False})

    try:
        data = json.loads(request.body)

        razorpay_payment_id = data.get("razorpay_payment_id")
        razorpay_order_id = data.get("razorpay_order_id")
        razorpay_signature = data.get("razorpay_signature")

        client = razorpay.Client(auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        ))

        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        })

        checkout_data = request.session.get("checkout_data")

        if not checkout_data:
            return JsonResponse({"success": False, "message": "Session expired"})

        registration = Registration.objects.get(id=checkout_data["registration_id"])
        cart = Cart.objects.get(id=checkout_data["cart_id"])

        items = cart.items.select_related("product", "variant")

        # ✅ SHIPPING AGAIN (IMPORTANT)
        subtotal = cart.subtotal()
        shipping = calculate_shipping(subtotal)
        total = subtotal - cart.coupon_discount + shipping

        # ✅ CREATE ORDER AFTER PAYMENT
        order = Order.objects.create(
            registration=registration,
            first_name=checkout_data["first_name"],
            email=checkout_data["email"],
            phone=checkout_data["phone"],
            address=checkout_data["address"],
            town=checkout_data["town"],
            state=checkout_data["state"],
            pincode=checkout_data["pincode"],
            land_mark=checkout_data["land_mark"],
            subtotal=subtotal,
            total=total,
            coupon_code=cart.coupon_code,
            coupon_discount=cart.coupon_discount,
            payment_method="razorpay",
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            payment_status=True
        )

        for item in items:
            variant = item.variant

            if variant.stock < item.quantity:
                return JsonResponse({"success": False, "message": "Stock issue"})

            variant.stock -= item.quantity
            variant.save()

            OrderItem.objects.create(
                order=order,
                product=item.product,
                variant=variant,
                quantity=item.quantity,
                price=item.price
            )

        cart.items.all().delete()
        cart.coupon_code = None
        cart.coupon_discount = Decimal("0.00")
        cart.save()

        del request.session["checkout_data"]

        from django.urls import reverse

        return JsonResponse({
            "success": True,
            "redirect_url": reverse("order_success") + f"?order_id={order.id}"
        })

    except Exception:
        return JsonResponse({"success": False})
    
@login_required
def order_success(request):
    order_id = request.GET.get("order_id")
    order = None

    if order_id:
        order = Order.objects.filter(
            id=order_id,
            registration__authuser=request.user   # ✅ FIX HERE
        ).first()

    return render(request, "order_success.html", {"order": order})


@login_required(login_url='home')
def profile(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        profile.phone = request.POST.get("phone", "").strip()
        profile.address = request.POST.get("address", "").strip()
        profile.town = request.POST.get("town", "").strip()
        profile.state = request.POST.get("state", "").strip()
        profile.pincode = request.POST.get("pincode", "").strip()
        profile.land_mark = request.POST.get("land_mark", "").strip()

        if "image" in request.FILES:
            profile.image = request.FILES["image"]

        profile.save()
        messages.success(request, "Profile updated successfully!")

    return render(request, "profile.html", {"profile": profile})


@login_required
def my_orders(request):
    registration = get_object_or_404(Registration, authuser=request.user)

    orders = (
        Order.objects
        .filter(registration=registration)
        .prefetch_related(
            "items__product",
            "items__variant__color",
            "items__variant__size"
        )
        .order_by("-created_at")
    )

    current_time = timezone.now()

    for order in orders:

        # ✅ Cancel time (based on order created)
        order.cancel_seconds = (current_time - order.created_at).total_seconds()

        # ✅ Return time (based on delivery time)
        if order.delivered_at:
            order.return_seconds = (current_time - order.delivered_at).total_seconds()
        else:
            order.return_seconds = None

    return render(request, "my_orders.html", {
        "orders": orders,
    })

@login_required
def return_policy(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    return render(request, "return_policy.html", {"order": order})

@login_required
def confirm_return(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if not order.return_requested:
        order.return_requested = True
        order.return_requested_at = timezone.now()
        order.save()

    return redirect("my_orders")

@role_required(["admin", "Accountant"])
def return_report(request):

    orders = Order.objects.filter(return_requested=True).order_by("-created_at")

    total_requests = orders.count()
    approved_returns = orders.filter(refund_processed=True).count()
    pending_returns = orders.filter(refund_processed=False).count()

    return render(request, "return_report.html", {
        "orders": orders,
        "total_requests": total_requests,
        "approved_returns": approved_returns,
        "pending_returns": pending_returns,
    })

@role_required(["admin", "Accountant"])
def return_requests(request):
    orders = Order.objects.filter(return_requested=True, refund_processed=False)
    return render(request, "return_requests.html", {"orders": orders})


@login_required
def confirm_cod_cancel(request, order_id):
    registration = get_object_or_404(Registration, authuser=request.user)
    order = get_object_or_404(Order, id=order_id, registration=registration)

    if request.method == "POST":

        if (
            order.payment_method == "cod" and
            not order.cancel_requested and
            not order.is_cancelled and
            not order.is_delivered
        ):
            # Mark cancelled
            order.is_cancelled = True
            order.cancel_requested = False
            order.save()

            # ✅ Restore stock
            for item in order.items.all():
                product_or_variant = item.variant if item.variant else item.product
                product_or_variant.stock += item.quantity
                product_or_variant.save()

            messages.success(request, "COD order cancelled successfully.")

        else:
            messages.error(request, "Cannot cancel this order.")

    return redirect("my_orders")

@user_passes_test(
    lambda u: u.is_authenticated and u.is_staff,
    login_url='user_login'
)


@login_required
@role_required(["admin", "Accountant", "Staff"])
def dashboard(request):
    today = now().date()

    # ✅ Role-based orders
    if request.user.is_superuser or request.user.groups.filter(name="Accountant").exists():
        orders = Order.objects.all().order_by('-created_at')
    else:
        orders = Order.objects.filter(is_pos_order=True).order_by('-created_at')

    # ✅ Paid orders (clean + strict)
    paid_orders = orders.filter(
        payment_status=True,
        is_cancelled=False,
        refund_processed=False,
        return_approved=False
    )

    # ✅ Revenue
    total_revenue = paid_orders.aggregate(total=Sum("total"))["total"] or Decimal("0.00")

    today_revenue = paid_orders.filter(
        created_at__date=today
    ).aggregate(total=Sum("total"))["total"] or Decimal("0.00")

    # ✅ Order counts
    total_orders = orders.count()
    total_paid_orders = paid_orders.count()

    # ✅ Pending orders
    pending_orders = orders.filter(
        is_cancelled=False
    ).exclude(
        is_delivered=True
    ).exclude(
        is_completed=True
    ).count()

    # ✅ POS pending payments
    pos_pending_payment = orders.filter(
        is_pos_order=True,
        payment_status=False,
        is_cancelled=False
    ).count()

    # ✅ Customers & Products
    total_customers = Registration.objects.count()
    total_products = Product.objects.count()

    # ✅ Refund & Return Requests
    pending_refunds = Order.objects.filter(
        cancel_requested=True,
        refund_processed=False
    )
    refund_count = pending_refunds.count()

    new_refunds_count = pending_refunds.filter(
        created_at__gte=now() - timedelta(days=1)
    ).count()

    return_requests = Order.objects.filter(
        return_requested=True,
        refund_processed=False
    )
    return_requests_count = return_requests.count()

    new_return_requests_count = return_requests.filter(
        created_at__gte=now() - timedelta(days=1)
    ).count()
    shipping_orders_count = orders.filter(
    is_shipped=True,
    is_delivered=False,
    is_cancelled=False
    ).count()

    # ✅ Profit / Income Calculation
    total_income = Decimal("0.00")

    order_items = OrderItem.objects.filter(
        order__payment_status=True,
        order__is_cancelled=False,
        order__refund_processed=False,
        order__return_approved=False
    ).select_related("product", "order")

    for item in order_items:
        if item.product and item.product.cost_price:

            order = item.order
            item_total = item.price * item.quantity

            # ✅ Coupon distribution
            if order.coupon_discount and order.subtotal and order.subtotal > 0:
                proportion = item_total / order.subtotal
                item_coupon_discount = (order.coupon_discount * proportion).quantize(Decimal("0.01"))
            else:
                item_coupon_discount = Decimal("0.00")

            profit_per_item = item.price - item.product.cost_price

            # ✅ FINAL NET PROFIT
            total_profit = (profit_per_item * item.quantity) - item_coupon_discount

            total_income += total_profit

    # ✅ Context
    context = {
        "total_revenue": total_revenue,
        "today_revenue": today_revenue,
        "total_net_income": total_income,

        "total_orders": total_orders,
        "paid_orders": total_paid_orders,
        "pending_orders": pending_orders,

        "pos_pending_payment": pos_pending_payment,

        "total_customers": total_customers,
        "total_products": total_products,

        "refund_count": refund_count if refund_count > 0 else None,
        "new_refunds_count": new_refunds_count if new_refunds_count > 0 else None,

        "return_requests_count": return_requests_count if return_requests_count > 0 else None,
        "new_return_requests_count": new_return_requests_count if new_return_requests_count > 0 else None,
        "shipping_orders_count": shipping_orders_count,

        "orders": orders,
    }

    return render(request, "dashboard.html", context)

@role_required(["Admin"])
def contact_list(request):
    contacts = Contact.objects.all().order_by('-id')
    return render(request, 'contact_list.html', {'contacts': contacts})

@role_required(["Admin"])
def delete_contact(request, contact_id):
    contact = get_object_or_404(Contact, id=contact_id)
    contact.delete()
    messages.success(request, "Contact message deleted successfully!")
    return redirect('contact_list')

@staff_member_required
def add_category(request):
    if request.method == "POST":
        Category.objects.create(name=request.POST.get("name"))
        return redirect("category_list")
    return render(request, "add_category.html")

@staff_member_required
def category_list(request):
    categories = Category.objects.all().order_by("id")
    return render(request, "category_list.html", {
        "categories": categories
    })
@staff_member_required
def edit_category(request, id):
    category = get_object_or_404(Category, id=id)
    if request.method == "POST":
        category.name = request.POST.get("name")
        category.save()
        return redirect("category_list")
    return render(request, "edit_category.html", {
        "category": category
    })

@staff_member_required
def delete_category(request, id):
    category = get_object_or_404(Category, id=id)
    category.delete()
    return redirect("category_list")

@staff_member_required
def add_subcategory(request):
    categories = Category.objects.all()
    if request.method == "POST":
        SubCategory.objects.create(
            name=request.POST.get("name"),
            category_id=request.POST.get("category")
        )
        return redirect("subcategory_list")
    return render(request, "add_subcategory.html", {"categories": categories})

@staff_member_required
def subcategory_list(request):
    subcategories = SubCategory.objects.select_related("category").all()
    return render(request, "subcategory_list.html", {
        "subcategories": subcategories
    })

@staff_member_required
def edit_subcategory(request, id):
    subcategory = get_object_or_404(SubCategory, id=id)
    categories = Category.objects.all()
    if request.method == "POST":
        subcategory.name = request.POST.get("name")
        subcategory.category_id = request.POST.get("category")
        subcategory.save()
        return redirect("subcategory_list")
    return render(request, "edit_subcategory.html", {
        "subcategory": subcategory,
        "categories": categories
    })

@staff_member_required
def delete_subcategory(request, id):
    subcategory = get_object_or_404(SubCategory, id=id)
    subcategory.delete()
    return redirect("subcategory_list")


def add_product(request):

    subcategories = SubCategory.objects.all()
    sizes = Size.objects.all()

    if request.method == "POST":

        name = request.POST.get("name")
        brand = request.POST.get("brand")
        product_code = request.POST.get("product_code")
        description = request.POST.get("description")
        subcategory_id = request.POST.get("subcategory")

        price = request.POST.get("price")
        cost_price = request.POST.get("cost_price")
        old_price = request.POST.get("old_price")

        status = True if request.POST.get("status") else False
        is_signature_collection = True if request.POST.get("is_signature_collection") else False
        is_featured = True if request.POST.get("is_featured") else False
        is_best_seller = True if request.POST.get("is_best_seller") else False

        additional_info = request.POST.get("additional_info")

        try:
            additional_info = json.loads(additional_info) if additional_info else {}
        except:
            additional_info = {}

        try:
            product = Product.objects.create(
                name=name,
                brand=brand,
                product_code=product_code,
                description=description,
                subcategory_id=subcategory_id,
                price=price,
                cost_price=cost_price if cost_price else None,
                old_price=old_price if old_price else None,
                status=status,
                is_signature_collection=is_signature_collection,
                is_featured=is_featured,
                is_best_seller=is_best_seller,
                additional_info=additional_info,
                image1=request.FILES.get("image1"),
                image2=request.FILES.get("image2"),
                image3=request.FILES.get("image3"),
                image4=request.FILES.get("image4"),
                image5=request.FILES.get("image5"),
            )
        except IntegrityError:
            messages.error(request, "Product with same code already exists!")
            return redirect("add_product")

        # ✅ VARIANTS
        color_names = request.POST.getlist("color_name[]")
        color_hex = request.POST.getlist("color_hex[]")
        sizes_list = request.POST.getlist("variant_size[]")
        stocks = request.POST.getlist("variant_stock[]")

        total_stock = 0

        for i in range(len(stocks)):

            stock = int(stocks[i]) if stocks[i] else 0
            total_stock += stock

            color_name = color_names[i].strip() if i < len(color_names) else ""
            color_hex_code = color_hex[i] if i < len(color_hex) else "#000000"
            size_id = sizes_list[i] if i < len(sizes_list) else None

            color_obj = None

            if color_name:
                color_obj, _ = ProductColor.objects.get_or_create(
                    product=product,
                    name=color_name,
                    defaults={"hex_code": color_hex_code}
                )

            size_obj = Size.objects.filter(id=size_id).first() if size_id else None

            ProductVariant.objects.create(
                product=product,
                color=color_obj,
                size=size_obj,
                stock=stock
            )

        product.stock = total_stock
        product.save()

        messages.success(request, "Product added successfully!")
        return redirect("product_list")

    return render(request, "add_product.html", {
        "subcategories": subcategories,
        "sizes": sizes
    })

def ajax_validate_product_code(request):
    product_code = request.GET.get("product_code", "").strip()

    exists = Product.objects.filter(product_code=product_code).exists()

    return JsonResponse({
        "exists": exists
    })

@staff_member_required
def product_list(request):
    products = Product.objects.all()
    return render(request, "product_list.html", {
        "products": products
    })


@staff_member_required
@transaction.atomic
def edit_product(request, slug):
    product = get_object_or_404(Product, slug=slug)
    subcategories = SubCategory.objects.all()
    sizes = Size.objects.all()

    if request.method == "POST":

        product.name = request.POST.get("name")
        product.brand = request.POST.get("brand")
        product.product_code = request.POST.get("product_code")
        product.subcategory_id = request.POST.get("subcategory")

        product.price = request.POST.get("price")
        product.cost_price = request.POST.get("cost_price") or None
        product.old_price = request.POST.get("old_price") or None

        product.description = request.POST.get("description")

        product.status = bool(request.POST.get("status"))
        product.is_signature_collection = bool(request.POST.get("is_signature_collection"))
        product.is_featured = bool(request.POST.get("is_featured"))
        product.is_best_seller = bool(request.POST.get("is_best_seller"))

        for i in range(1,6):
            img = request.FILES.get(f"image{i}")
            if img:
                setattr(product,f"image{i}",img)

        product.save()

        # delete old variants
        ProductVariant.objects.filter(product=product).delete()
        ProductColor.objects.filter(product=product).delete()

        color_names = request.POST.getlist("color_name[]")
        color_hexes = request.POST.getlist("color_hex[]")
        size_ids = request.POST.getlist("variant_size[]")
        stocks = request.POST.getlist("variant_stock[]")

        total_stock = 0
        created_colors = {}

        for i in range(len(stocks)):

            color_name = color_names[i].strip() if i < len(color_names) else ""
            color_hex = color_hexes[i] if i < len(color_hexes) else "#000000"
            size_id = size_ids[i] if i < len(size_ids) else None
            stock_value = int(stocks[i] or 0)

            color_obj = None

            # create color only if exists
            if color_name:
                if color_name not in created_colors:
                    color_obj = ProductColor.objects.create(
                        product=product,
                        name=color_name,
                        hex_code=color_hex
                    )
                    created_colors[color_name] = color_obj
                else:
                    color_obj = created_colors[color_name]

            ProductVariant.objects.create(
                product=product,
                color=color_obj,
                size_id=size_id if size_id else None,
                stock=stock_value
            )

            total_stock += stock_value

        product.stock = total_stock
        product.save()

        return redirect("product_list")

    variants = ProductVariant.objects.filter(product=product).select_related("color","size")

    return render(request,"edit_product.html",{
        "product":product,
        "subcategories":subcategories,
        "sizes":sizes,
        "variants":variants
    })

@staff_member_required
def delete_product(request, slug):
    product = get_object_or_404(Product, slug=slug)
    product.delete()
    messages.success(request, "Product deleted")
    return redirect("product_list")

@staff_member_required
def add_size(request):
    if request.method == "POST":
        Size.objects.create(
            name=request.POST.get("name"),
            order=request.POST.get("order")
        )
        return redirect("size_list")
    return render(request, "add_size.html")

@staff_member_required
def size_list(request):
    sizes = Size.objects.all().order_by("order")
    return render(request, "size_list.html", {
        "sizes": sizes
    })

@staff_member_required
def edit_size(request, id):
    size = get_object_or_404(Size, id=id)
    if request.method == "POST":
        size.name = request.POST.get("name")
        size.order = request.POST.get("order")
        size.save()
        return redirect("size_list")
    return render(request, "edit_size.html", {
        "size": size
    })

@staff_member_required
def delete_size(request, id):
    size = get_object_or_404(Size, id=id)
    size.delete()
    return redirect("size_list")


@staff_member_required
def add_coupon(request):
    if request.method == "POST":
        Coupon.objects.create(
            code=request.POST.get("code"),
            discount_amount=request.POST.get("discount"),
            min_cart_value=request.POST.get("min_cart"),
            expiry_date=request.POST.get("expiry")
        )
        return redirect("coupon_list")
    return render(request, "add_coupon.html")

@staff_member_required
def coupon_list(request):
    coupons = Coupon.objects.all().order_by("-id")
    return render(request, "coupon_list.html", {"coupons": coupons})

@staff_member_required
def edit_coupon(request, id):
    coupon = get_object_or_404(Coupon, id=id)
    if request.method == "POST":
        coupon.code = request.POST.get("code")
        coupon.discount_amount = request.POST.get("discount")
        coupon.min_cart_value = request.POST.get("min_cart")
        coupon.expiry_date = request.POST.get("expiry")
        coupon.save()
        return redirect("coupon_list")
    return render(request, "edit_coupon.html", {"coupon": coupon})

@staff_member_required
def delete_coupon(request, id):
    coupon = get_object_or_404(Coupon, id=id)
    coupon.delete()
    return redirect("coupon_list")

def article_list(request):
    articles = Article.objects.all().order_by('-posted_on')
    return render(request, 'article_list.html', {'articles': articles})

def add_article(request):
    form = ArticleForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Article Added Successfully")
        return redirect('article_list')
    return render(request, 'add_article.html', {'form': form})

def edit_article(request, slug):
    article = get_object_or_404(Article, slug=slug)
    if request.method == "POST":
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        if not title or not content:
            messages.error(request, "Title and content required")
            return redirect('edit_article', slug=slug)
        article.title = title
        article.content = content
        if request.FILES.get('image'):
            article.image = request.FILES.get('image')
        article.save()
        messages.success(request, "Article Updated Successfully")
        return redirect('article_list')
    return render(request, 'edit_article.html', {'article': article})

def delete_article(request, slug):
    article = get_object_or_404(Article, slug=slug)
    article.delete()
    messages.success(request, "Article Deleted Successfully")
    return redirect('article_list')

from django.db.models import Q, Sum
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from datetime import datetime

@role_required(["Accountant"])
@login_required(login_url='user_login')
def report_page(request):

    orders = Order.objects.all()

    # ================= DATE FILTER =================
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    if from_date:
        orders = orders.filter(created_at__date__gte=datetime.strptime(from_date, "%Y-%m-%d"))

    if to_date:
        orders = orders.filter(created_at__date__lte=datetime.strptime(to_date, "%Y-%m-%d"))

    # ================= PAYMENT FILTER =================
    payment = request.GET.get('payment')

    if payment:
        if payment == "cod":
            orders = orders.filter(payment_method="cod", is_pos_order=False)

        elif payment == "razorpay":
            orders = orders.filter(payment_method="razorpay", is_pos_order=False)

        elif payment == "pos_paid":
            orders = orders.filter(is_pos_order=True, payment_status=True)

        elif payment == "pos_pending":
            orders = orders.filter(is_pos_order=True, payment_status=False)

    # ================= STATUS FILTER =================
    status = request.GET.get('status')

    if status:
        if status == "pending":
            orders = orders.filter(
                is_delivered=False,
                is_cancelled=False
            ).exclude(
                is_pos_order=True,
                payment_status=True
            )

        elif status == "completed":
            # Include delivered online orders OR POS paid orders
            orders = orders.filter(
                Q(is_delivered=True, is_cancelled=False, return_approved=False) |
                Q(is_pos_order=True, payment_status=True)
            )

        elif status == "cancelled":
            orders = orders.filter(is_cancelled=True)

        elif status == "returned":
            orders = orders.filter(return_approved=True)

    # ================= COUNTS =================
    total_orders = orders.count()

    # ✅ VALID REVENUE = delivered online orders (exclude cancelled, returned, refunded)
    valid_orders = orders.filter(
        is_delivered=True,
        is_cancelled=False,
        return_approved=False,
        refund_processed=False
    )

    total_revenue = valid_orders.aggregate(Sum('total'))['total__sum'] or 0

    # ✅ Paid orders = delivered online OR POS paid
    total_paid_orders = orders.filter(
        Q(is_delivered=True, is_cancelled=False, return_approved=False, refund_processed=False) |
        Q(is_pos_order=True, payment_status=True)
    ).count()

    # Pending orders = not delivered and not cancelled
    pending_orders = orders.filter(
        is_delivered=False,
        is_cancelled=False
    ).exclude(
        is_pos_order=True,
        payment_status=True
    ).count()

    # Returned orders
    returned_orders = orders.filter(return_approved=True).count()

    # ================= RESPONSE =================
    return render(request, "report_page.html", {
        "title": "Order Report",
        "orders": orders.order_by("-created_at"),
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "total_paid_orders": total_paid_orders,
        "pending_orders": pending_orders,
        "returned_orders": returned_orders,
    })

@role_required(["Accountant","Staff"])
@login_required(login_url='user_login')
@user_passes_test(staff_required, login_url='home')
def order_list(request):
    if request.user.is_superuser or request.user.groups.filter(name="Accountant").exists():
        orders = Order.objects.all()
    else:
        orders = Order.objects.filter(is_pos_order=True)
    orders = orders.order_by('-created_at')
    return render(request, 'orders_view.html', {
        'orders': orders,
        'title': 'All Orders'
    })

@role_required(["Accountant","Staff"])
@login_required(login_url='user_login')
@user_passes_test(staff_required, login_url='home')
def paid_orders(request):
    if request.user.is_superuser or request.user.groups.filter(name="Accountant").exists():
        orders = Order.objects.filter(payment_status=True, is_cancelled=False)
    else:
        orders = Order.objects.filter(
            is_pos_order=True,
            payment_status=True,
            is_cancelled=False
        )
    return render(request, 'orders_view.html', {
        'orders': orders.order_by('-created_at'),
        'title': 'Paid Orders'
    })

@role_required(["Accountant","Staff"])
@login_required(login_url='user_login')
@user_passes_test(staff_required, login_url='home')
def pending_orders(request):
    if request.user.is_superuser or request.user.groups.filter(name="Accountant").exists():
        # Only orders that are not cancelled, not delivered, and not paid
        orders = Order.objects.filter(
            is_cancelled=False,
            is_delivered=False,
            payment_status=False  # <-- add this
        )
    else:
        orders = Order.objects.filter(
            is_pos_order=True,
            is_cancelled=False,
            is_delivered=False,
            payment_status=False  # <-- add this
        )

    return render(request, 'orders_view.html', {
        'orders': orders.order_by('-created_at'),
        'title': 'Pending Orders'
    })

@role_required(["Accountant","Staff"])
@login_required(login_url='user_login')
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    show_pos_payment_buttons = order.is_pos_order and not order.payment_status
    if order.is_pos_order:
        payment_display = order.pos_payment_type.capitalize() if order.pos_payment_type else "Pending POS"
    else:
        if order.payment_method == "razorpay":
            payment_display = "Razorpay"
        elif order.payment_method == "cod":
            payment_display = "Cash on Delivery"
        else:
            payment_display = order.get_payment_method_display()
    return render(request, "order_detail.html", {
        "order": order,
        "show_pos_payment_buttons": show_pos_payment_buttons,
        "payment_display": payment_display,
    })

def mark_order_completed(request, order_id):

    if request.method != "POST":
        return redirect("order_detail", order_id=order_id)

    order = get_object_or_404(Order, id=order_id)

    if order.is_cancelled or order.refund_processed:
        messages.error(request, "Cannot process this order.")
        return redirect("order_detail", order_id=order.id)

    # ✅ SHIPPING START
    order.is_completed = True
    order.is_shipped = True
    order.payment_status = True

    reference = request.POST.get("reference")
    if reference:
        order.reference = reference

    order.save()

    messages.success(request, "Order moved to Shipping Processing.")

    # 🔥 REDIRECT TO NEW PAGE
    return redirect("delivery_page", order_id=order.id)
@login_required
@role_required(['admin','Accountant'])
def mark_as_delivered(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.is_cancelled or order.refund_processed:
        return redirect("order_detail", order_id=order.id)

    order.is_delivered = True
    order.delivered_at = timezone.now()  # ✅ ADD THIS
    order.save()

    return redirect("order_detail", order_id=order.id)

@role_required(["Accountant","Staff"])
@login_required
def delivery_page(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    return render(request, "delivery_page.html", {
        "order": order
    })

@role_required(["Accountant","Staff"])
@login_required
def shipping_orders(request):
    orders = Order.objects.filter(
        is_shipped=True
    ).order_by("-created_at")

    return render(request, "shipping_orders.html", {
        "orders": orders
    })

@role_required(["Accountant","Staff"])
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.is_cancelled:
        messages.warning(request, "Order already cancelled.")
        return redirect("dashboard")
    if not order.is_delivered:
        for item in order.items.all():
            if hasattr(item, "variant") and item.variant:
                item.variant.stock = F("stock") + item.quantity
                item.variant.save(update_fields=["stock"])
            else:
                item.product.stock = F("stock") + item.quantity
                item.product.save(update_fields=["stock"])
        if order.payment_method == "razorpay" and order.payment_status:
            try:
                client = razorpay.Client(auth=(
                    settings.RAZORPAY_KEY_ID,
                    settings.RAZORPAY_KEY_SECRET
                ))
                refund_amount = int(order.total * 100)
                refund = client.payment.refund(
                    order.razorpay_payment_id,
                    {
                        "amount": refund_amount,
                        "speed": "normal"
                    }
                )
                order.refund_id = refund["id"]
                order.refund_status = True
                order.refund_processed = True

                messages.success(request, "Order cancelled and Razorpay refund initiated.")
            except Exception as e:
                print("Refund Error:", e)
                messages.error(request, "Order cancelled but refund failed.")
        else:
            messages.success(request, "Order cancelled and stock restored.")
        order.is_cancelled = True
        order.save()
    return redirect("dashboard")

@role_required(["Accountant","Staff"])
@login_required
def reference_detail(request, name):
    orders = Order.objects.filter(reference=name)

    total_orders = orders.count()
    total_amount = orders.aggregate(total=Sum("total"))["total"] or 0

    return render(request, "reference_detail.html", {
        "reference_name": name,
        "orders": orders,
        "total_orders": total_orders,
        "total_amount": total_amount,
    })


@role_required(["Accountant","Staff"])
@login_required
def pos_payment_complete(request, order_id):
    order = get_object_or_404(Order, id=order_id, is_pos_order=True)
    if request.method == "POST" and not order.payment_status:
        order.payment_status = True
        order.is_completed = True
        order.save()
        messages.success(request, f"POS Payment for Order #{order.id} marked as complete.")
    return redirect("dashboard")

@role_required(["Accountant","Staff"])
def cancel_pos_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, is_pos_order=True)
    if order.is_cancelled:
        messages.warning(request, "Order already cancelled.")
        return redirect("order_detail", order_id=order.id)
    for item in order.items.all():
        if hasattr(item, "variant") and item.variant:
            item.variant.stock = F('stock') + item.quantity
            item.variant.save(update_fields=["stock"])
        else:
            item.product.stock = F('stock') + item.quantity
            item.product.save(update_fields=["stock"])
    order.payment_status = False
    order.is_completed = False
    order.is_cancelled = True
    order.save(update_fields=["payment_status", "is_completed", "is_cancelled"])

    messages.warning(request, f"POS Payment for Order #{order.id} has been canceled and stock restored.")
    return redirect("order_detail", order_id=order.id)

@role_required(["Accountant","Staff"])
@login_required(login_url='user_login')
def customer_list(request):
    customers = Registration.objects.select_related('authuser').all().order_by('-id')
    return render(request, 'customers_view.html', {
        'customers': customers
    })
@role_required(["Accountant","Staff"])
@role_required(["Accountant","Staff"])
def shipping_address_list(request):
    orders = Order.objects.all().order_by('-created_at')  
    context = {
        'title': 'Shipping Address List',
        'orders': orders
    }
    return render(request, 'shipping_address_list.html', context)

@role_required(["Accountant"])
@login_required(login_url='user_login')
def add_terms(request):
    terms = TermsCondition.objects.first()
    if request.method == "POST":
        form = TermsForm(request.POST, instance=terms)
        if form.is_valid():
            form.save()
            return redirect("terms_list")
    else:
        form = TermsForm(instance=terms)
    return render(request, "add_terms.html", {"form": form, "terms": terms})

@role_required(["Accountant"])
@login_required(login_url='user_login')
def terms_list(request):
    terms = TermsCondition.objects.all().order_by("-updated_at")
    return render(request, "terms_list.html", {"terms": terms})

@role_required(["Accountant"])
@login_required(login_url='user_login')
def edit_terms(request, pk):
    terms = get_object_or_404(TermsCondition, pk=pk)
    if request.method == "POST":
        form = TermsForm(request.POST, instance=terms)
        if form.is_valid():
            form.save()
            return redirect("terms_list")
    else:
        form = TermsForm(instance=terms)
    return render(request, "add_terms.html", {"form": form, "terms": terms})

@role_required(["Accountant"])
@login_required(login_url='user_login')
def delete_terms(request, pk):
    terms = get_object_or_404(TermsCondition, pk=pk)
    terms.delete()
    return redirect("terms_list")


def terms_page(request):
    terms = TermsCondition.objects.first()
    return render(request, "terms_page.html", {"terms": terms})

@role_required(["Accountant"])
@login_required(login_url='user_login')
def add_privacy(request):
    privacy = PrivacyPolicy.objects.first()
    if request.method == "POST":
        form = PrivacyForm(request.POST, instance=privacy)
        if form.is_valid():
            form.save()
            return redirect("privacy_list")
    else:
        form = PrivacyForm(instance=privacy)
    return render(request, "add_privacy.html", {"form": form, "privacy": privacy})

@role_required(["Accountant"])
@login_required(login_url='user_login')
def privacy_list(request):
    privacy = PrivacyPolicy.objects.all().order_by("-updated_at")
    return render(request, "privacy_list.html", {"privacy": privacy})

@role_required(["Accountant"])
@login_required(login_url='user_login')
def edit_privacy(request, pk):
    privacy = get_object_or_404(PrivacyPolicy, pk=pk)
    if request.method == "POST":
        form = PrivacyForm(request.POST, instance=privacy)
        if form.is_valid():
            form.save()
            return redirect("privacy_list")
    else:
        form = PrivacyForm(instance=privacy)
    return render(request, "add_privacy.html", {"form": form, "privacy": privacy})

@role_required(["Accountant"])
@login_required(login_url='user_login')
def delete_privacy(request, pk):
    privacy = get_object_or_404(PrivacyPolicy, pk=pk)
    privacy.delete()
    return redirect("privacy_list")


def privacy_page(request):
    privacy = PrivacyPolicy.objects.first()
    return render(request, "privacy_page.html", {"privacy": privacy})

@role_required(["Accountant"])
@staff_member_required
def review_list(request):
    reviews = Review.objects.select_related('product').order_by('-created_at')
    return render(request, 'review_list.html', {'reviews': reviews})

@role_required(["Accountant"])
@staff_member_required
def delete_review(request, id):
    review = get_object_or_404(Review, id=id)
    if request.method == "POST":
        review.delete()
        return redirect('review_list')
    return render(request, 'delete_review.html', {'review': review})

@role_required(["Accountant"])
def faq_list(request):
    faqs = FAQ.objects.all().order_by("-created_at")
    return render(request, "faq_list.html", {"faqs": faqs})

@role_required(["Accountant"])
@login_required(login_url='user_login')
def add_faq(request):
    if request.method == "POST":
        form = FAQForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("faq_list")
    else:
        form = FAQForm()
    return render(request, "add_faq.html", {"form": form})

@role_required(["Accountant"])
@login_required(login_url='user_login')
def edit_faq(request, pk):
    faq = get_object_or_404(FAQ, pk=pk)
    if request.method == "POST":
        form = FAQForm(request.POST, instance=faq)
        if form.is_valid():
            form.save()
            return redirect("faq_list")
    else:
        form = FAQForm(instance=faq)
    return render(request, "add_faq.html", {"form": form, "faq": faq})

@role_required(["Accountant"])
@login_required(login_url='user_login')
def delete_faq(request, pk):
    faq = get_object_or_404(FAQ, pk=pk)
    faq.delete()
    return redirect("faq_list")

def faq_page(request):
    faqs = FAQ.objects.all().order_by("created_at")
    return render(request, "faq_page.html", {"faqs": faqs})

@role_required(["Accountant"])
@staff_member_required
def pos_page(request):
    products = Product.objects.filter(status=True).select_related(
    "subcategory__category"
).prefetch_related(
    "variants__color",
    "variants__size"
)
    return render(request, "pos.html", {"products": products})

@role_required(["Accountant","Staff"])
@staff_member_required
@csrf_exempt
@transaction.atomic
def pos_create_order(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request"})

    try:
        data = json.loads(request.body)

        items = data.get("items", [])
        customer_name = data.get("customer_name")
        customer_phone = data.get("customer_phone")
        pos_payment_type = data.get("pos_payment_type")
        reference = data.get("reference", "").strip()

        # ✅ NEW: get discount
        discount_amount = Decimal(str(data.get("discount_amount", 0)))

        if not items:
            return JsonResponse({"status": "error", "message": "Cart is empty"})

        if not customer_name or not customer_phone:
            return JsonResponse({"status": "error", "message": "Customer details required"})

        total_amount = Decimal("0.00")

        # ✅ Create order first
        order = Order.objects.create(
            registration=None,
            first_name=customer_name,
            phone=customer_phone,
            payment_method="pos",              # ✅ IMPORTANT FIX
            pos_payment_type=pos_payment_type,
            payment_status=True,
            is_completed=True,

            # ✅ AUTO DELIVERY FOR POS
            is_shipped=True,
            is_delivered=True,
            delivered_at=timezone.now(),

            is_pos_order=True,
            reference=reference,
            subtotal=0,
            total=0,
            coupon_discount=Decimal("0.00")
        )

        for item in items:
            product = Product.objects.select_for_update().get(id=item["id"])
            quantity = int(item["quantity"])
            price = Decimal(str(item["price"]))
            variant_data = item.get("variant")

            if variant_data:
                variant = ProductVariant.objects.select_for_update().get(id=variant_data["id"])

                if variant.stock < quantity:
                    raise Exception(f"{product.name} stock not enough")

                variant.stock -= quantity
                variant.save()

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    variant=variant,
                    quantity=quantity,
                    price=price
                )
            else:
                if product.stock < quantity:
                    raise Exception(f"{product.name} stock not enough")

                product.stock -= quantity
                product.save()

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=price
                )

            total_amount += price * quantity

        # ✅ APPLY DISCOUNT SAFELY
        if discount_amount < 0:
            discount_amount = Decimal("0.00")

        if discount_amount > total_amount:
            discount_amount = total_amount

        final_total = total_amount - discount_amount

        # ✅ SAVE FINAL VALUES
        order.subtotal = total_amount
        order.coupon_discount = discount_amount
        order.total = final_total
        order.save()

        return JsonResponse({"status": "success"})

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        })
    
@role_required(["Accountant","Staff"])
@staff_member_required
def pos_edit_page(request, order_id):
    order = Order.objects.get(id=order_id, is_pos_order=True)
    products = Product.objects.filter(status=True).select_related(
    "subcategory__category"
    ).prefetch_related(
    "variants__color",
    "variants__size")
    order_items = OrderItem.objects.filter(order=order)
    return render(request, "pos_edit.html", {
        "order": order,
        "products": products,
        "order_items": order_items
    })

@role_required(["Accountant","Staff"])
@require_POST
@staff_member_required
@transaction.atomic
def pos_update_order(request, order_id):
    try:
        data = json.loads(request.body)

        items = data.get("items", [])
        pos_payment_type = data.get("pos_payment_type")
        customer_name = data.get("customer_name")
        customer_phone = data.get("customer_phone")
        discount_amount = Decimal(str(data.get("discount_amount", 0)))
        order = Order.objects.select_for_update().get(
            id=order_id,
            is_pos_order=True
        )
        old_items = OrderItem.objects.filter(order=order)

        for old_item in old_items:
            if old_item.variant:
                old_item.variant.stock += old_item.quantity
                old_item.variant.save()
            else:
                old_item.product.stock += old_item.quantity
                old_item.product.save()

        old_items.delete()
        subtotal = Decimal("0.00")

        for item in items:
            quantity = int(item.get("quantity", 0))
            if quantity <= 0:
                continue

            variant_data = item.get("variant")

            if variant_data:
                variant = ProductVariant.objects.select_for_update().get(
                    id=variant_data["id"]
                )

                if variant.stock < quantity:
                    raise Exception(f"{variant.product.name} stock not enough")

                # create item
                OrderItem.objects.create(
                    order=order,
                    product=variant.product,
                    variant=variant,
                    quantity=quantity,
                    price=variant.product.price
                )

                # reduce stock
                variant.stock -= quantity
                variant.save()

                subtotal += variant.product.price * quantity

            else:
                product = Product.objects.select_for_update().get(
                    id=item["id"]
                )

                if product.stock < quantity:
                    raise Exception(f"{product.name} stock not enough")

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=product.price
                )

                product.stock -= quantity
                product.save()

                subtotal += product.price * quantity
        if discount_amount > subtotal:
            discount_amount = subtotal

        final_total = subtotal - discount_amount
        order.subtotal = subtotal
        order.coupon_discount = discount_amount
        order.total = final_total
        order.pos_payment_type = pos_payment_type

        if customer_name:
            order.first_name = customer_name

        if customer_phone:
            order.phone = customer_phone

        order.save()

        return JsonResponse({"status": "success"})

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        })
    
@role_required(["Accountant"])
@staff_member_required
def total_income_page(request):

    order_items = OrderItem.objects.filter(
        order__payment_status=True,
        order__is_cancelled=False,
        order__refund_processed=False
    ).select_related("product", "order")

    product_data = []
    total_income = Decimal("0.00")
    total_revenue = Decimal("0.00")
    total_discount = Decimal("0.00")

    for item in order_items:
        if item.product and item.product.cost_price:

            order = item.order
            item_total = item.price * item.quantity

            # Proportional coupon discount for this item
            if order.coupon_discount and order.subtotal and order.subtotal > 0:
                proportion = item_total / order.subtotal
                item_coupon_discount = (order.coupon_discount * proportion).quantize(Decimal("0.01"))
            else:
                item_coupon_discount = Decimal("0.00")

            effective_selling = item_total - item_coupon_discount
            profit_per_item = item.price - item.product.cost_price
            total_profit = (profit_per_item * item.quantity) - item_coupon_discount
            total_selling = item_total

            total_income += total_profit
            total_revenue += effective_selling
            total_discount += item_coupon_discount

            product_data.append({
                "product": item.product,
                "quantity": item.quantity,
                "selling_price": item.price,
                "cost_price": item.product.cost_price,
                "coupon_discount": item_coupon_discount,
                "effective_selling": effective_selling,
                "profit_per_item": profit_per_item,
                "total_profit": total_profit,
                "total_selling": total_selling,
                "has_coupon": item_coupon_discount > 0,
            })

    return render(request, "total_income.html", {
        "title": "Total Income Report",
        "products": product_data,
        "total_income": total_income,
        "total_revenue": total_revenue,
        "total_discount": total_discount,
    })

@role_required(["Accountant"])
def create_user(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        group_name = request.POST.get("group")
        if User.objects.filter(username=username).exists():
            messages.error(request,"Username already exists")
            return redirect("create_user")
        if User.objects.filter(email=email).exists():
            messages.error(request,"Email already exists")
            return redirect("create_user")
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        group = Group.objects.get(name=group_name)
        user.groups.add(group)
        user.is_staff = True
        user.save()
        messages.success(request,"Employee Created Successfully")
        return redirect("employee_list")
    return render(request,"create_user.html")

def employee_list(request):
    employees = User.objects.filter(
        groups__name__in=["Accountant", "Staff"]
    ).distinct()
    return render(request,"employee_list.html",{
        "employees":employees
    })


@role_required(["Accountant"])
@login_required(login_url="user_login")
def delete_employee(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user.is_superuser:
        messages.error(request, "Admin cannot be deleted")
        return redirect("employee_list")
    user.delete()
    messages.success(request, "Employee deleted successfully")
    return redirect("employee_list")

@login_required
def cancel_policy(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request,"cancel_policy.html",{
        "order":order
    })


@login_required
def confirm_cancel_request(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # ❌ Prevent duplicate cancel requests
    if order.cancel_requested:
        messages.warning(request, "Cancellation already requested.")
        return redirect("my_orders")

    # ✅ ADD THIS BLOCK (24-hour restriction)
    if timezone.now() > order.created_at + timedelta(hours=24):
        messages.error(request, "❌ Cancellation period expired (24 hours).")
        return redirect("my_orders")

    # Update order status
    order.cancel_requested = True
    order.cancel_requested_at = timezone.now()
    order.save()

    # ✅ Payment method (Django choice display)
    payment_method = order.get_payment_method_display()

    # Email subject
    subject = f"🚨 Cancel Request - Order #{order.id}"

    # TEXT VERSION (fallback)
    text_content = f"""
Cancel request received for Order #{order.id}

Customer: {order.first_name}
Email: {order.email}
Phone: {order.phone}
Amount: ₹{order.total}
Payment Method: {payment_method}

Please review and process this request.
"""

    # HTML EMAIL
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background:#f4f6fb; padding:20px;">
        
        <div style="max-width:600px; margin:auto; background:white; padding:25px; border-radius:10px; box-shadow:0 5px 15px rgba(0,0,0,0.1);">

            <h2 style="color:#ff4d4d; text-align:center;">🚨 Cancel Request Received</h2>

            <p style="font-size:15px; color:#333;">
                A customer has requested to cancel an order. Here are the details:
            </p>

            <table style="width:100%; border-collapse:collapse; margin-top:15px;">
                
                <tr>
                    <td style="padding:10px; border-bottom:1px solid #ddd;"><b>Order ID</b></td>
                    <td style="padding:10px; border-bottom:1px solid #ddd;">#{order.id}</td>
                </tr>

                <tr>
                    <td style="padding:10px; border-bottom:1px solid #ddd;"><b>Name</b></td>
                    <td style="padding:10px; border-bottom:1px solid #ddd;">{order.first_name}</td>
                </tr>

                <tr>
                    <td style="padding:10px; border-bottom:1px solid #ddd;"><b>Email</b></td>
                    <td style="padding:10px; border-bottom:1px solid #ddd;">{order.email}</td>
                </tr>

                <tr>
                    <td style="padding:10px; border-bottom:1px solid #ddd;"><b>Phone</b></td>
                    <td style="padding:10px; border-bottom:1px solid #ddd;">{order.phone}</td>
                </tr>

                <tr>
                    <td style="padding:10px; border-bottom:1px solid #ddd;"><b>Payment Method</b></td>
                    <td style="padding:10px; border-bottom:1px solid #ddd;">{payment_method}</td>
                </tr>

                <tr>
                    <td style="padding:10px;"><b>Total Amount</b></td>
                    <td style="padding:10px;">₹{order.total}</td>
                </tr>

            </table>

            <div style="margin-top:25px; padding:15px; background:#fff3f3; border-left:5px solid #ff4d4d; border-radius:8px;">
                <strong>⚠️ Action Required:</strong><br>
                Please review and process this cancellation request.
            </div>

            <p style="text-align:center; margin-top:20px; font-size:12px; color:#999;">
                Trendo Admin Notification System
            </p>

        </div>

    </body>
    </html>
    """

    # Send email
    email = EmailMultiAlternatives(
        subject,
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        [settings.ADMIN_EMAIL],
    )
    email.attach_alternative(html_content, "text/html")
    email.send()

    messages.success(request, "Cancellation request sent successfully.")
    return redirect("my_orders")
@login_required
def cod_cancel_policy(request, order_id):
    registration = get_object_or_404(Registration, authuser=request.user)
    order = get_object_or_404(Order, id=order_id, registration=registration)

    if order.payment_method != "cod":
        messages.error(request, "Invalid request.")
        return redirect("my_orders")

    # Only allow cancel if within 24 hours, not delivered or cancelled
    current_time = timezone.now()
    seconds_passed = (current_time - order.created_at).total_seconds()
    can_cancel = (
        seconds_passed <= 86400 and 
        not order.is_cancelled and 
        not order.is_delivered and
        not order.cancel_requested
    )

    return render(request, "cod_cancel_policy.html", {
        "order": order,
        "can_cancel": can_cancel,
    })

@login_required
def confirm_cod_cancel(request, order_id):
    registration = get_object_or_404(Registration, authuser=request.user)
    order = get_object_or_404(Order, id=order_id, registration=registration)

    if request.method == "POST":

        if order.payment_method == "cod" and not order.cancel_requested and not order.is_cancelled:

            # ✅ Update order
            order.cancel_requested = True
            order.cancel_requested_at = timezone.now()
            order.save()

            # ✅ Payment method (will show "Cash on Delivery")
            payment_method = order.get_payment_method_display()

            # ✅ Email subject
            subject = f"🚨 COD Cancel Request - Order #{order.id}"

            # ✅ TEXT VERSION
            text_content = f"""
COD cancel request received for Order #{order.id}

Customer: {order.first_name}
Email: {order.email}
Phone: {order.phone}
Amount: ₹{order.total}
Payment Method: {payment_method}

Please review and process this request.
"""

            # ✅ HTML EMAIL
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; background:#f4f6fb; padding:20px;">
                
                <div style="max-width:600px; margin:auto; background:white; padding:25px; border-radius:10px; box-shadow:0 5px 15px rgba(0,0,0,0.1);">

                    <h2 style="color:#ff6f61; text-align:center;">📦 COD Cancellation Request</h2>

                    <p style="font-size:15px; color:#333;">
                        A customer has requested to cancel a <b>Cash on Delivery</b> order.
                    </p>

                    <table style="width:100%; border-collapse:collapse; margin-top:15px;">
                        
                        <tr>
                            <td style="padding:10px; border-bottom:1px solid #ddd;"><b>Order ID</b></td>
                            <td style="padding:10px; border-bottom:1px solid #ddd;">#{order.id}</td>
                        </tr>

                        <tr>
                            <td style="padding:10px; border-bottom:1px solid #ddd;"><b>Name</b></td>
                            <td style="padding:10px; border-bottom:1px solid #ddd;">{order.first_name}</td>
                        </tr>

                        <tr>
                            <td style="padding:10px; border-bottom:1px solid #ddd;"><b>Email</b></td>
                            <td style="padding:10px; border-bottom:1px solid #ddd;">{order.email}</td>
                        </tr>

                        <tr>
                            <td style="padding:10px; border-bottom:1px solid #ddd;"><b>Phone</b></td>
                            <td style="padding:10px; border-bottom:1px solid #ddd;">{order.phone}</td>
                        </tr>

                        <tr>
                            <td style="padding:10px; border-bottom:1px solid #ddd;"><b>Payment Method</b></td>
                            <td style="padding:10px; border-bottom:1px solid #ddd;">{payment_method}</td>
                        </tr>

                        <tr>
                            <td style="padding:10px;"><b>Total Amount</b></td>
                            <td style="padding:10px;">₹{order.total}</td>
                        </tr>

                    </table>

                    <div style="margin-top:25px; padding:15px; background:#fff3f3; border-left:5px solid #ff6f61; border-radius:8px;">
                        <strong>⚠️ Action Required:</strong><br>
                        Please review and process this cancellation request.
                    </div>

                    <p style="text-align:center; margin-top:20px; font-size:12px; color:#999;">
                        Trendo Admin Notification System
                    </p>

                </div>

            </body>
            </html>
            """

            # ✅ Send email
            email = EmailMultiAlternatives(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            messages.success(request, "COD order cancel request sent successfully.")

        else:
            messages.error(request, "Cannot cancel this order.")

    return redirect("my_orders")

@role_required(["Accountant"])
def refund_requests(request):
    orders = Order.objects.filter(
        cancel_requested=True,
        refund_processed=False
    ).order_by("-created_at")
    return render(request, "refund_requests.html", {"orders": orders})



logger = logging.getLogger(__name__)
@role_required(["Accountant","admin"])
@transaction.atomic
def process_refund(request, order_id):
    if request.method != "POST":
        return redirect("refund_requests")

    order = get_object_or_404(Order, id=order_id)

    if order.refund_processed:
        logger.warning(f"Order #{order.id} already processed.")
        return redirect("refund_requests")

    try:

        # =========================
        # 🟢 RAZORPAY REFUND
        # =========================
        if order.payment_method != "cod" and order.razorpay_payment_id:

            client = razorpay.Client(auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET
            ))

            payment = client.payment.fetch(order.razorpay_payment_id)
            captured_amount = payment.get("amount", 0)

            refund_amount = int(order.total * 100)

            if refund_amount > captured_amount:
                refund_amount = captured_amount

            refund = client.payment.refund(
                order.razorpay_payment_id,
                {"amount": refund_amount, "speed": "normal"}
            )

            order.refund_id = refund.get("id")

        # =========================
        # 🟢 COD → NO REFUND API
        # =========================
        if order.payment_method == "cod":
            order.refund_status = False  # no refund money

        # =========================
        # UPDATE ORDER STATUS
        # =========================
        order.refund_processed = True
        order.is_cancelled = True
        order.save()

        # =========================
        # 🔁 RESTORE STOCK (COMMON)
        # =========================
        for item in order.items.all():
            product_or_variant = item.variant if item.variant else item.product
            product_or_variant.stock += item.quantity
            product_or_variant.save()

        # =========================
        # 📦 BUILD EMAIL CONTENT
        # =========================
        items_html = ""
        text_items = ""

        for item in order.items.all():
            if item.variant:
                variant_details = []
                if hasattr(item.variant, "size") and item.variant.size:
                    variant_details.append(str(item.variant.size))
                if hasattr(item.variant, "color") and item.variant.color:
                    variant_details.append(str(item.variant.color))

                variant_str = " / ".join(variant_details)

                product_name = f"{escape(item.variant.product.name)}"
                if variant_str:
                    product_name += f" ({variant_str})"

                brand_name = getattr(item.variant.product, "brand", "")
            else:
                product_name = escape(item.product.name)
                brand_name = getattr(item.product, "brand", "")

            qty = item.quantity

            items_html += f"""
            <tr>
                <td style="padding:10px; border-bottom:1px solid #eee;">{product_name}</td>
                <td style="padding:10px; border-bottom:1px solid #eee;">{brand_name}</td>
                <td style="padding:10px; border-bottom:1px solid #eee;">{qty}</td>
            </tr>
            """

            text_items += f"- {product_name} ({brand_name}) x {qty}\n"

        # =========================
        # 📧 SUBJECT (COD vs REFUND)
        # =========================
        if order.payment_method == "cod":
            subject = f"Order Cancelled - Order #{order.id}"
            heading = "Order Cancelled ❌"
            message_line = "Your COD order has been cancelled successfully."
            extra_note = "No payment was collected for this order."
        else:
            subject = f"Refund Approved - Order #{order.id}"
            heading = "Refund Approved ✅"
            message_line = "Your refund request has been approved and processed successfully."
            extra_note = "Refund will be credited within 3–10 business days."

        # =========================
        # 📩 EMAIL TEMPLATE (SAME STYLE)
        # =========================
        text_content = f"""
Hello {order.first_name},

{message_line}

Order ID: #{order.id}
Amount: ₹{order.total}

Items:
{text_items}

{extra_note}

Thank you.
"""

        html_content = f"""
<html>
<body style="margin:0; padding:0; background:#f4f6fb; font-family: Arial, sans-serif;">
<div style="max-width:600px; margin:30px auto; background:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 10px 30px rgba(0,0,0,0.1);">

    <div style="background:#28a745; padding:20px; text-align:center;">
        <h2 style="color:#fff; margin:0;">{heading}</h2>
    </div>

    <div style="padding:30px; color:#333;">
        <p>Hello <b>{escape(order.first_name)}</b>,</p>

        <p>{message_line}</p>

        <table style="width:100%; border-collapse:collapse; margin-top:20px;">
            <tr>
                <td style="padding:10px; border-bottom:1px solid #eee;"><b>Order ID</b></td>
                <td style="padding:10px; border-bottom:1px solid #eee;">#{order.id}</td>
            </tr>
            <tr>
                <td style="padding:10px; border-bottom:1px solid #eee;"><b>Amount</b></td>
                <td style="padding:10px; border-bottom:1px solid #eee;">₹{order.total}</td>
            </tr>
            <tr>
                <td style="padding:10px;"><b>Payment Method</b></td>
                <td style="padding:10px;">{order.get_payment_method_display()}</td>
            </tr>
        </table>

        <h4 style="margin-top:20px;">Items:</h4>

        <table style="width:100%; border-collapse:collapse;">
            <tr>
                <th style="text-align:left; padding:10px; border-bottom:1px solid #ddd;">Product</th>
                <th style="text-align:left; padding:10px; border-bottom:1px solid #ddd;">Brand</th>
                <th style="text-align:left; padding:10px; border-bottom:1px solid #ddd;">Quantity</th>
            </tr>
            {items_html}
        </table>

        <p style="margin-top:20px; color:#555;">
            {extra_note}
        </p>

        <hr style="margin:25px 0;">

        <p style="text-align:center; font-size:13px; color:#999;">
            Thank you for shopping with us ❤️
        </p>
    </div>

</div>
</body>
</html>
"""

        # =========================
        # 📤 SEND EMAIL
        # =========================
        email = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [order.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

    except razorpay.errors.BadRequestError as e:
        logger.error(f"Razorpay refund failed for Order #{order.id}: {str(e)}")
        raise e

    except Exception as e:
        logger.error(f"Refund failed for Order #{order.id}: {str(e)}")
        raise e

    return redirect("refund_requests")

@role_required(["Accountant", "admin"])
@transaction.atomic
def process_return(request, order_id):

    if request.method != "POST":
        return redirect("return_requests")

    order = get_object_or_404(Order, id=order_id)

    if order.refund_processed:
        logger.warning(f"Order #{order.id} already processed.")
        return redirect("return_requests")

    try:
        is_cod = order.payment_method == "cod"

        # =========================
        # 💳 RAZORPAY REFUND (ONLY IF PAID ONLINE)
        # =========================
        if not is_cod and order.razorpay_payment_id:

            client = razorpay.Client(auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET
            ))

            payment = client.payment.fetch(order.razorpay_payment_id)
            captured_amount = payment.get("amount", 0)

            refund_amount = int(order.total * 100)

            if refund_amount > captured_amount:
                refund_amount = captured_amount

            refund = client.payment.refund(
                order.razorpay_payment_id,
                {"amount": refund_amount}
            )

            order.refund_id = refund.get("id")
            order.refund_status = True

        # =========================
        # 💵 COD RETURN (NO REFUND)
        # =========================
        if is_cod:
            order.refund_status = False

        # =========================
        # ❌ DO NOT RESTORE STOCK
        # =========================
        # (INTENTIONALLY NO STOCK UPDATE)

        # =========================
        # ✅ UPDATE STATUS
        # =========================
        order.return_approved = True
        order.refund_processed = True
        order.is_cancelled = False
        order.save()

        # =========================
        # 📧 EMAIL CONTENT
        # =========================
        if is_cod:
            subject = f"Return Approved - Order #{order.id}"
            heading = "Return Approved 🔄"
            message_line = "Your return request has been approved."
            extra_note = "Our team will contact you for pickup."
        else:
            subject = f"Return & Refund Processed - Order #{order.id}"
            heading = "Return & Refund Successful ✅"
            message_line = "Your return has been approved and refund processed."
            extra_note = "Refund will be credited within 3–10 business days."

        text_content = f"""
Hello {order.first_name},

{message_line}

Order ID: #{order.id}
Amount: ₹{order.total}

{extra_note}

Thank you.
"""

        html_content = f"""
<html>
<body style="font-family: Arial; background:#f4f6fb; padding:20px;">
<div style="max-width:600px;margin:auto;background:white;padding:25px;border-radius:10px;">

<h2 style="text-align:center;color:#28a745;">{heading}</h2>

<p>Hello <b>{escape(order.first_name)}</b>,</p>
<p>{message_line}</p>

<p><b>Order ID:</b> #{order.id}</p>
<p><b>Amount:</b> ₹{order.total}</p>

<p style="margin-top:20px;">{extra_note}</p>

</div>
</body>
</html>
"""

        email = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [order.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

    except Exception as e:
        logger.error(f"Return failed: {str(e)}")
        raise e

    return redirect("return_requests")


@role_required(["Admin","Accountant"])
def refund_report(request):
    orders = Order.objects.filter(cancel_requested=True).order_by("-created_at")
    total_requests = Order.objects.filter(cancel_requested=True).count()
    approved_refunds = Order.objects.filter(
        cancel_requested=True,
        refund_processed=True
    ).count()
    pending_refunds = Order.objects.filter(
        cancel_requested=True,
        refund_processed=False
    ).count()
    return render(request,"refund_report.html",{
        "orders":orders,
        "total_requests":total_requests,
        "approved_refunds":approved_refunds,
        "pending_refunds":pending_refunds
    })

# LIST
def banner_list(request):
    banners = HomeBanner.objects.all()
    return render(request, "banner_list.html", {"banners": banners})


# ADD
def add_banner(request):
    if request.method == "POST":
        HomeBanner.objects.create(
            title_line1=request.POST.get("title_line1"),
            title_line2=request.POST.get("title_line2"),
            subtitle=request.POST.get("subtitle"),
            image=request.FILES.get("image"),
            mobile_image=request.FILES.get("mobile_image"),  )
        return redirect("banner_list")

    return render(request, "add_banner.html")


# EDIT
def edit_banner(request, id):
    banner = get_object_or_404(HomeBanner, id=id)

    if request.method == "POST":
        banner.title_line1 = request.POST.get("title_line1")
        banner.title_line2 = request.POST.get("title_line2")
        banner.subtitle = request.POST.get("subtitle")

        # ✅ Desktop image
        if request.FILES.get("image"):
            banner.image = request.FILES.get("image")

        # ✅ Mobile image (ADD HERE 👇)
        if request.FILES.get("mobile_image"):
            banner.mobile_image = request.FILES.get("mobile_image")

        banner.save()
        return redirect("banner_list")

    return render(request, "edit_banner.html", {"banner": banner})


# DELETE
def delete_banner(request, id):
    banner = get_object_or_404(HomeBanner, id=id)
    banner.delete()
    return redirect("banner_list")