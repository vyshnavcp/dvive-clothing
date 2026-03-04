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



def home(request):
   blogs = Article.objects.order_by('-posted_on')[:4]
   best_seller_products = Product.objects.filter(is_best_seller=True)[:5]
   featured_product= Product.objects.filter(is_featured=True)[:5]
   signature_products = Product.objects.filter( is_signature_collection=True,status=True)[:8]
   categories = Category.objects.prefetch_related("subcategories").all()
   return render(request, "home.html", {'blogs': blogs,'best_seller_products': best_seller_products,'featured_product':featured_product,'signature_products': signature_products,"categories": categories})

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
from django.core.paginator import Paginator
from django.db.models import Count



def product(request, slug=None):
    products = Product.objects.filter(status=True).distinct()
    query = request.GET.get('q')
    if query:
        products = products.filter(name__icontains=query)
    subcategory_counts = SubCategory.objects.annotate(
        product_count=Count('products', distinct=True)
    )
    size_counts = Size.objects.annotate(
    product_count=Count('productvariant__product', distinct=True))
    if slug:
        products = products.filter(subcategory__slug=slug)
        pagination_base = reverse('filter_by_subcategory', args=[slug])
        active_slug = slug
    else:
        pagination_base = reverse('product')
        active_slug = None
    size_filter = request.GET.get('size')
    if size_filter:
        products = products.filter(
            variants__size__name=size_filter).distinct()
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

@staff_member_required
@transaction.atomic
def add_product(request):
    subcategories = SubCategory.objects.all()
    sizes = Size.objects.all()
    if request.method == "POST":
        product = Product.objects.create(
            name=request.POST.get("name"),
            brand=request.POST.get("brand"),
            product_code=request.POST.get("product_code"),
            subcategory_id=request.POST.get("subcategory"),
            price=request.POST.get("price"),
            cost_price=request.POST.get("cost_price") or None,
            old_price=request.POST.get("old_price") or None,
            description=request.POST.get("description"),
            additional_info=request.POST.get("additional_info") or {},
            image1=request.FILES.get("image1"),
            image2=request.FILES.get("image2"),
            image3=request.FILES.get("image3"),
            image4=request.FILES.get("image4"),
            image5=request.FILES.get("image5"),
            status=bool(request.POST.get("status")),
            is_signature_collection=bool(request.POST.get("is_signature_collection")),
            is_featured=bool(request.POST.get("is_featured")),
            is_best_seller=bool(request.POST.get("is_best_seller")),
        )
        color_names = request.POST.getlist("color_name[]")
        color_hexes = request.POST.getlist("color_hex[]")
        size_ids = request.POST.getlist("variant_size[]")
        stocks = request.POST.getlist("variant_stock[]")

        total_stock = 0
        created_colors = {}

        for i in range(len(color_names)):

            if not color_names[i] or not size_ids[i]:
                continue
            if color_names[i] not in created_colors:
                color = ProductColor.objects.create(
                    product=product,
                    name=color_names[i],
                    hex_code=color_hexes[i]
                )
                created_colors[color_names[i]] = color
            else:
                color = created_colors[color_names[i]]

            stock_value = int(stocks[i] or 0)

            ProductVariant.objects.create(
                product=product,
                color=color,
                size_id=size_ids[i],
                stock=stock_value
            )

            total_stock += stock_value

        product.stock = total_stock
        product.save()
        return redirect("product_list")
    return render(request, "add_product.html", {
        "subcategories": subcategories,
        "sizes": sizes
    })

@staff_member_required
def product_list(request):
    products = Product.objects.select_related("subcategory").all()
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

        # BASIC FIELDS
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
        for i in range(1, 6):
            img = request.FILES.get(f"image{i}")
            if img:
                setattr(product, f"image{i}", img)

        product.save()

        ProductVariant.objects.filter(product=product).delete()
        ProductColor.objects.filter(product=product).delete()

        color_names = request.POST.getlist("color_name[]")
        color_hexes = request.POST.getlist("color_hex[]")
        size_ids = request.POST.getlist("variant_size[]")
        stocks = request.POST.getlist("variant_stock[]")

        total_stock = 0
        created_colors = {}

        for i in range(len(color_names)):

            if not color_names[i] or not size_ids[i]:
                continue
            if color_names[i] not in created_colors:
                color = ProductColor.objects.create(
                    product=product,
                    name=color_names[i],
                    hex_code=color_hexes[i]
                )
                created_colors[color_names[i]] = color
            else:
                color = created_colors[color_names[i]]

            stock_value = int(stocks[i] or 0)

            ProductVariant.objects.create(
                product=product,
                color=color,
                size_id=size_ids[i],
                stock=stock_value
            )

            total_stock += stock_value

        product.stock = total_stock
        product.save()

        return redirect("product_list")

    variants = ProductVariant.objects.filter(product=product).select_related("color", "size")

    return render(request, "edit_product.html", {
        "product": product,
        "subcategories": subcategories,
        "sizes": sizes,
        "variants": variants
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
        if v.size_id and v.color_id:
            key = f"{v.color_id}-{v.size_id}"
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
    phone = request.POST['phone']
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
    return redirect('user_login')

def ajax_validate_register(request):
    email = request.GET.get('email', '').strip()
    phone = request.GET.get('phone', '').strip()
    password = request.GET.get('password', '').strip()
    name = request.GET.get('name', '').strip()
    data = {
        'email_error': '',
        'phone_error': '',
        'password_error': '',
        'name_error': '',
    }
    if name:
        if len(name) < 3:
            data['name_error'] = 'Name must be at least 3 characters'
        elif not re.match(r'^[A-Za-z ]+$', name):
            data['name_error'] = 'Name must contain only letters and spaces'
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if email:
        if not re.match(email_regex, email):
            data['email_error'] = 'Enter a valid email address'
        elif User.objects.filter(username=email).exists():
            data['email_error'] = 'Email already exists'
    if phone:
        if not phone.isdigit():
            data['phone_error'] = 'Phone must contain only numbers'
        elif len(phone) != 10:
            data['phone_error'] = 'Phone must be exactly 10 digits'
        elif Registration.objects.filter(phone=phone).exists():
            data['phone_error'] = 'Phone number already registered'
    if password:
        if len(password) < 8:
            data['password_error'] = 'Minimum 8 characters required'
        elif not re.search(r'[A-Z]', password):
            data['password_error'] = 'Must contain at least 1 uppercase letter'
        elif not re.search(r'[0-9]', password):
            data['password_error'] = 'Must contain at least 1 number'
        elif not re.search(r'[!@#$%^&*]', password):
            data['password_error'] = 'Must contain at least 1 special character (!@#$%^&*)'
    return JsonResponse(data)
def staff_required(user):
    return user.is_staff

def user_login(request):
    return render(request,'login.html')
def login_post(request):
    login_input = request.POST.get('name', '').strip()
    password = request.POST.get('password', '').strip()
    if not login_input:
        messages.error(request, "Username or Email is required")
        return redirect('user_login')
    if not password:
        messages.error(request, "Password is required")
        return redirect('user_login')
    try:
        user_obj = User.objects.get(email__iexact=login_input)
        username = user_obj.username
    except User.DoesNotExist:
        username = login_input
    user = authenticate(request, username=username, password=password)

    if user is not None:
        login(request, user)
        if user.is_staff:
            return redirect("dashboard")
        else:
            return redirect("home")

    else:
        messages.error(request, "Invalid username or password")
        return redirect('user_login')
def user_logout(request):
    logout(request)
    return redirect('user_login')

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

    if not size_id or not color_id:
        return JsonResponse({
            "success": False,
            "message": "Please select size and color."
        })
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
                        cart.coupon_code = coupon.code
                        cart.coupon_discount = coupon.discount_amount
                        message = "Coupon applied!"
                except Coupon.DoesNotExist:
                    cart.coupon_code = None
                    cart.coupon_discount = Decimal("0.00")
                    message = "Invalid coupon"

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
    })

@login_required
@transaction.atomic
def checkout_post(request):
    if request.method != "POST":
        return redirect("home")
    registration = get_object_or_404(Registration, authuser=request.user)
    cart = get_object_or_404(Cart, registration=registration)
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    items = cart.items.select_related("product", "variant")

    if not items.exists():
        messages.warning(request, "Your cart is empty")
        return redirect("cart_page")

    first_name = request.POST.get("first_name")
    email = request.POST.get("email")
    phone = request.POST.get("phone")
    address = request.POST.get("address")
    town = request.POST.get("town")
    state = request.POST.get("state")
    pincode = request.POST.get("pincode")
    land_mark = request.POST.get("land_mark")
    payment_method = request.POST.get("payment-option")

    profile.address = address
    profile.phone = phone
    profile.save()

    for item in items:
        if item.quantity > item.variant.stock:
            messages.error(
                request,
                f"{item.product.name} "
                f"({item.variant.color.name} - {item.variant.size.name}) "
                f"only {item.variant.stock} item(s) available."
            )
            return redirect("cart_page")
        
    if payment_method == "cod":

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
            subtotal=cart.subtotal(),
            total=cart.total(),
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
                variant=item.variant,  
                quantity=item.quantity,
                price=item.price
            )
        cart.items.all().delete()
        cart.coupon_code = None
        cart.coupon_discount = Decimal("0.00")
        cart.save()

        return redirect("cash_on_delivery_success", order_id=order.id)
    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    amount = int(cart.total() * 100)

    razorpay_order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": "1"
    })

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
        subtotal=cart.subtotal(),
        total=cart.total(),
        coupon_code=cart.coupon_code,
        coupon_discount=cart.coupon_discount,
        payment_method="razorpay",
        razorpay_order_id=razorpay_order["id"],
        payment_status=False
    )

    for item in items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            variant=item.variant,  
            quantity=item.quantity,
            price=item.price
        )
    return render(request, "checkout_payment.html", {
        "order": order,
        "razorpay_order_id": razorpay_order["id"],
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "amount": amount,
        "currency": "INR"
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
    state = request.GET.get("state")

    if state == "Kerala":
        shipping = Decimal("80.00")
    else:
        shipping = Decimal("120.00")
    registration = get_object_or_404(Registration, authuser=request.user)
    cart = get_object_or_404(Cart, registration=registration)
    subtotal = cart.subtotal()
    total = subtotal - cart.coupon_discount + shipping
    return JsonResponse({
        "shipping": shipping,
        "subtotal": subtotal,
        "total": total
    })

@csrf_exempt
@login_required
def payment_success_post(request):
    if request.method != "POST":
        return JsonResponse({"success": False})
    data = json.loads(request.body)
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_signature = data.get('razorpay_signature')
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        })
        order = get_object_or_404(Order, razorpay_order_id=razorpay_order_id)
        order.razorpay_payment_id = razorpay_payment_id
        order.payment_status = True
        order.save()
        for item in order.items.all():
            product = item.product
            if product.stock >= item.quantity:
                product.stock -= item.quantity
                product.save()
        cart = get_object_or_404(Cart, registration=order.registration)
        cart.items.all().delete()
        cart.coupon_code = None
        cart.coupon_discount = Decimal("0.00")
        cart.update_totals()
        return JsonResponse({"success": True})
    except razorpay.errors.SignatureVerificationError:
        return JsonResponse({"success": False})
    
@login_required
def order_success(request):
    return render(request, 'order_success.html')

@login_required
def profile(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        profile.phone = request.POST.get("phone", "").strip()
        profile.address = request.POST.get("address", "").strip()
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
        .prefetch_related("items__product", "items__color", "items__size")
        .order_by("-created_at")
    )
    return render(request, "my_orders.html", {
        "orders": orders
    })

from .decorators import role_required
@user_passes_test(
    lambda u: u.is_authenticated and u.is_staff,
    login_url='user_login'
)

def dashboard(request):
    today = now().date()
    if request.user.is_superuser:
        orders = Order.objects.all().order_by('-created_at')
    else:
        orders = Order.objects.filter(is_pos_order=True).order_by('-created_at')
    paid_orders = orders.filter(payment_status=True, is_cancelled=False)
    total_revenue = paid_orders.aggregate(total=Sum("total"))["total"] or 0
    today_revenue = paid_orders.filter(created_at__date=today).aggregate(total=Sum("total"))["total"] or 0
    total_orders = orders.count()
    total_paid_orders = paid_orders.count()
    pending_orders = orders.filter(payment_status=False, is_cancelled=False).count()
    pos_pending_payment = orders.filter(is_pos_order=True, payment_status=False, is_cancelled=False).count()
    total_customers = Registration.objects.count()
    total_products = Product.objects.count()
    total_income = Decimal("0.00")
    order_items = OrderItem.objects.filter(
        order__payment_status=True,
        order__is_cancelled=False
    ).select_related("product")
    for item in order_items:
        if item.product and item.product.cost_price:
            profit = (item.price - item.product.cost_price) * item.quantity
            total_income += profit
    context = {
        "total_revenue": total_revenue,
        "today_revenue": today_revenue,
        "total_income": total_income,  
        "total_orders": total_orders,
        "paid_orders": total_paid_orders,
        "pending_orders": pending_orders,
        "pos_pending_payment": pos_pending_payment,
        "total_customers": total_customers,
        "total_products": total_products,
        "orders": orders,
    }
    return render(request, "dashboard.html", context)

@login_required(login_url='user_login')
def report_page(request):
    orders = Order.objects.all()
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    if from_date:
        orders = orders.filter(created_at__date__gte=datetime.strptime(from_date, "%Y-%m-%d"))
    if to_date:
        orders = orders.filter(created_at__date__lte=datetime.strptime(to_date, "%Y-%m-%d"))
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
    status = request.GET.get('status')
    if status:
        if status == "pending":
            orders = orders.filter(is_delivered=False, is_cancelled=False)
        elif status == "completed":
            orders = orders.filter(is_delivered=True)
        elif status == "cancelled":
            orders = orders.filter(is_cancelled=True)
    total_orders = orders.count()
    total_revenue = orders.aggregate(Sum('total'))['total__sum'] or 0
    total_paid_orders = orders.filter(is_delivered=True).count()
    pending_orders = orders.filter(is_delivered=False, is_cancelled=False).count()
    return render(request, "report_page.html", {
        "title": "Order Report",
        "orders": orders.order_by("-created_at"),
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "total_paid_orders": total_paid_orders,
        "pending_orders": pending_orders,
    })

@login_required(login_url='user_login')
@user_passes_test(staff_required, login_url='home')
def order_list(request):
    if request.user.is_superuser:
        orders = Order.objects.all()
    else:
        orders = Order.objects.filter(is_pos_order=True)
    orders = orders.order_by('-created_at')
    return render(request, 'orders_view.html', {
        'orders': orders,
        'title': 'All Orders'
    })


@login_required(login_url='user_login')
@user_passes_test(staff_required, login_url='home')
def paid_orders(request):
    if request.user.is_superuser:
        orders = Order.objects.filter(payment_status=True, is_cancelled=False)
    else:
        orders = Order.objects.filter(is_pos_order=True, payment_status=True, is_cancelled=False)
    return render(request, 'orders_view.html', {
        'orders': orders.order_by('-created_at'),
        'title': 'Paid Orders'
    })


@login_required(login_url='user_login')
@user_passes_test(staff_required, login_url='home')
def pending_orders(request):
    if request.user.is_superuser:
        orders = Order.objects.filter(payment_status=False, is_cancelled=False)
    else:
        orders = Order.objects.filter(is_pos_order=True, payment_status=False, is_cancelled=False)
    return render(request, 'orders_view.html', {
        'orders': orders.order_by('-created_at'),
        'title': 'Pending Orders'
    })

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
    order = get_object_or_404(Order, id=order_id)

    if request.method == "POST":
        reference = request.POST.get("reference", "").strip()

        order.reference = reference
        order.is_completed = True
        order.is_delivered = True

        if order.payment_method == "cod":
            order.payment_status = True

        order.save()

        messages.success(request, "Order marked as completed.")

        return redirect("dashboard")

    return redirect("dashboard")
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

def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.is_cancelled:
        messages.warning(request, "Order already cancelled.")
        return redirect("dashboard")

    if not order.is_delivered:
        for item in order.items.all():
            if hasattr(item, "variant") and item.variant:
                item.variant.stock = F('stock') + item.quantity
                item.variant.save(update_fields=["stock"])
            else:
                item.product.stock = F('stock') + item.quantity
                item.product.save(update_fields=["stock"])
        order.is_cancelled = True
        order.save(update_fields=["is_cancelled"])
        messages.success(request, "Order cancelled and stock restored.")
    return redirect("dashboard")

@login_required
def pos_payment_complete(request, order_id):
    order = get_object_or_404(Order, id=order_id, is_pos_order=True)
    if request.method == "POST" and not order.payment_status:
        order.payment_status = True
        order.is_completed = True
        order.save()
        messages.success(request, f"POS Payment for Order #{order.id} marked as complete.")
    return redirect("dashboard")

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


@login_required(login_url='user_login')
def customer_list(request):
    customers = Registration.objects.all().order_by('-id')
    return render(request, 'customers_view.html', {
        'customers': customers
    })
def shipping_address_list(request):
    orders = Order.objects.all().order_by('-created_at')  
    context = {
        'title': 'Shipping Address List',
        'orders': orders
    }
    return render(request, 'shipping_address_list.html', context)

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

@login_required(login_url='user_login')
def terms_list(request):
    terms = TermsCondition.objects.all().order_by("-updated_at")
    return render(request, "terms_list.html", {"terms": terms})

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

@login_required(login_url='user_login')
def delete_terms(request, pk):
    terms = get_object_or_404(TermsCondition, pk=pk)
    terms.delete()
    return redirect("terms_list")
def terms_page(request):
    terms = TermsCondition.objects.first()
    return render(request, "terms_page.html", {"terms": terms})

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


@login_required(login_url='user_login')
def privacy_list(request):
    privacy = PrivacyPolicy.objects.all().order_by("-updated_at")
    return render(request, "privacy_list.html", {"privacy": privacy})


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

@login_required(login_url='user_login')
def delete_privacy(request, pk):
    privacy = get_object_or_404(PrivacyPolicy, pk=pk)
    privacy.delete()
    return redirect("privacy_list")

def privacy_page(request):
    privacy = PrivacyPolicy.objects.first()
    return render(request, "privacy_page.html", {"privacy": privacy})

@staff_member_required
def review_list(request):
    reviews = Review.objects.select_related('product').order_by('-created_at')
    return render(request, 'review_list.html', {'reviews': reviews})

@staff_member_required
def delete_review(request, id):
    review = get_object_or_404(Review, id=id)
    if request.method == "POST":
        review.delete()
        return redirect('review_list')
    return render(request, 'delete_review.html', {'review': review})

def faq_list(request):
    faqs = FAQ.objects.all().order_by("-created_at")
    return render(request, "faq_list.html", {"faqs": faqs})


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

@login_required(login_url='user_login')
def delete_faq(request, pk):
    faq = get_object_or_404(FAQ, pk=pk)
    faq.delete()
    return redirect("faq_list")

def faq_page(request):
    faqs = FAQ.objects.all().order_by("created_at")
    return render(request, "faq_page.html", {"faqs": faqs})

@staff_member_required
def pos_page(request):
    products = Product.objects.filter(status=True).prefetch_related(
        "variants__color",
        "variants__size"
    )
    return render(request, "pos.html", {"products": products})

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
        if not items:
            return JsonResponse({"status": "error", "message": "Cart is empty"})
        if not customer_name or not customer_phone:
            return JsonResponse({"status": "error", "message": "Customer details required"})
        total_amount = Decimal("0.00")
        order = Order.objects.create(
            registration=None,
            first_name=customer_name,
            phone=customer_phone,
            payment_method="pos",
            pos_payment_type=pos_payment_type,
            payment_status=True,
            is_completed=True,
            is_pos_order=True,
            reference=reference, 
            subtotal=0,
            total=0
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
        order.subtotal = total_amount
        order.total = total_amount
        order.save()
        return JsonResponse({"status": "success"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})

@staff_member_required
def pos_edit_page(request, order_id):
    order = Order.objects.get(id=order_id, is_pos_order=True)
    products = Product.objects.filter(status=True)
    order_items = OrderItem.objects.filter(order=order)
    return render(request, "pos_edit.html", {
        "order": order,
        "products": products,
        "order_items": order_items
    })

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
        order = Order.objects.select_for_update().get(
            id=order_id,
            is_pos_order=True
        )
        old_items = OrderItem.objects.filter(order=order)
        for old_item in old_items:
            if hasattr(old_item, "variant") and old_item.variant:
                old_item.variant.stock += old_item.quantity
                old_item.variant.save()
            else:
                old_item.product.stock += old_item.quantity
                old_item.product.save()
        old_items.delete()
        subtotal = Decimal("0.00")
        for item in items:
            quantity = int(item.get("quantity", 0))
            variant_data = item.get("variant")
            if quantity <= 0:
                continue
            if variant_data:
                variant = ProductVariant.objects.select_for_update().get(
                    id=variant_data["id"]
                )
                if variant.stock < quantity:
                    raise Exception(f"{variant.product.name} stock not enough")
                OrderItem.objects.create(
                    order=order,
                    product=variant.product,
                    variant=variant,
                    quantity=quantity,
                    price=variant.product.price
                )
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
        order.subtotal = subtotal
        order.total = subtotal
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

@staff_member_required
def total_income_page(request):
    order_items = OrderItem.objects.filter(
        order__is_cancelled=False,
        order__is_delivered=True
    ).select_related("product")
    product_data = []
    total_income = 0
    for item in order_items:
        if item.product.cost_price:
            profit_per_item = item.price - item.product.cost_price
            total_profit = profit_per_item * item.quantity
            total_income += total_profit
            product_data.append({
                "product": item.product,
                "quantity": item.quantity,
                "selling_price": item.price,
                "cost_price": item.product.cost_price,
                "profit_per_item": profit_per_item,
                "total_profit": total_profit
            })
    return render(request, "total_income.html", {
        "title": "Total Income Report",
        "products": product_data,
        "total_income": total_income
    })
