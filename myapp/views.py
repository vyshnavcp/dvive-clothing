from datetime import date
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
from django.db.models import Count
from django.contrib.auth.decorators import login_required
import razorpay
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


def home(request):
   blogs = Article.objects.order_by('-posted_on')[:4]
   best_seller_products = Product.objects.filter(is_best_seller=True)[:5]
   featured_product= Product.objects.filter(is_featured=True)[:5]
   signature_products = Product.objects.filter( is_signature_collection=True,status=True)[:8]

   return render(request, "home.html", {'blogs': blogs,'best_seller_products': best_seller_products,'featured_product':featured_product,'signature_products': signature_products,})


def about(request):
    return render(request, "about.html")

def blog(request):
    blogs_list = Article.objects.all().order_by('-posted_on')
    paginator = Paginator(blogs_list, 4)  # 4 blogs per page

    page_number = request.GET.get('page')
    blogs = paginator.get_page(page_number)

    return render(request, 'blog.html', {'blogs': blogs})

def blog_detail(request, slug):
    blog_detail = get_object_or_404(Article, slug=slug)
    return render(request, 'blog_detail.html', {'blog': blog_detail})
def contact(request):
    if request.method == "POST":
        Contact.objects.create(
            name=request.POST.get('name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            subject=request.POST.get('subject'),
            message=request.POST.get('comment'),
        )
        return JsonResponse({"status": "success", "message": "Message sent successfully!"})

    return render(request, "contact.html")


def product(request, slug=None):
    products = Product.objects.all()

    #  SEARCH
    query = request.GET.get('q')
    if query:
        products = products.filter(name__icontains=query)

    # category counts
    subcategory_counts = SubCategory.objects.annotate(
        product_count=Count('products')
    )

    # size counts
    size_counts = Size.objects.annotate(
        product_count=Count('product')
    )

    # category filter
    if slug:
        products = products.filter(subcategory__slug=slug)
        pagination_base = reverse('filter_by_subcategory', args=[slug])
        active_slug = slug
    else:
        pagination_base = reverse('product')
        active_slug = None

    # size filter
    size_filter = request.GET.get('size')
    if size_filter:
        products = products.filter(sizes__name=size_filter)
    if request.GET.get('signature') == '1':
        products = products.filter(
            is_signature_collection=True,
            status=True
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
        'search_query': query,   # 👈 important
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
def add_product(request):
    subcategories = SubCategory.objects.all()
    sizes = Size.objects.all()

    if request.method == "POST":
        # -------- JSON VALIDATION --------
        additional_info_raw = request.POST.get("additional_info", "").strip()
        try:
            additional_info = json.loads(additional_info_raw) if additional_info_raw else {}
            if not isinstance(additional_info, dict):
                raise ValueError
        except Exception:
            messages.error(request, "Additional Info must be valid JSON.")
            return render(request, "add_product.html", {
                "subcategories": subcategories,
                "sizes": sizes,
            })

        # -------- PRODUCT CREATE --------
        product = Product.objects.create(
            name=request.POST.get("name"),
            brand=request.POST.get("brand"),
            product_code=request.POST.get("product_code"),
            slug=request.POST.get("slug") or slugify(request.POST.get("name")),
            description=request.POST.get("description"),
            price=request.POST.get("price"),
            old_price=request.POST.get("old_price") or None,
            stock=request.POST.get("stock"),
            subcategory_id=request.POST.get("subcategory"),

            status=bool(request.POST.get("status")),
            is_signature_collection=bool(request.POST.get("is_signature_collection")),
            is_featured=bool(request.POST.get("is_featured")),
            is_best_seller=bool(request.POST.get("is_best_seller")),

            additional_info=additional_info,

            image1=request.FILES.get("image1"),
            image2=request.FILES.get("image2"),
            image3=request.FILES.get("image3"),
            image4=request.FILES.get("image4"),
            image5=request.FILES.get("image5"),
        )

        product.sizes.set(request.POST.getlist("sizes"))

        messages.success(request, "Product added successfully.")
        return redirect("product_list")

    return render(request, "add_product.html", {
        "subcategories": subcategories,
        "sizes": sizes,
    })
@staff_member_required
def product_list(request):
    products = Product.objects.select_related("subcategory").all()
    return render(request, "product_list.html", {
        "products": products
    })

@staff_member_required
def edit_product(request, slug):
    product = get_object_or_404(Product, slug=slug)
    subcategories = SubCategory.objects.all()
    sizes = Size.objects.all()

    # ✅ Convert dict → JSON string (VERY IMPORTANT)
    additional_info_json = json.dumps(
        product.additional_info or {},
        indent=4
    )

    if request.method == "POST":
        raw_json = request.POST.get("additional_info", "").strip()

        try:
            additional_info = json.loads(raw_json) if raw_json else {}
            if not isinstance(additional_info, dict):
                raise ValueError
        except Exception:
            messages.error(request, "Additional Info must be valid JSON")
            return render(request, "edit_product.html", {
                "product": product,
                "subcategories": subcategories,
                "sizes": sizes,
                "additional_info_json": raw_json,  # keep user input
            })

        # ---------- SAVE ----------
        product.name = request.POST.get("name")
        product.slug = request.POST.get("slug") or slugify(product.name)
        product.brand = request.POST.get("brand")
        product.product_code = request.POST.get("product_code")
        product.subcategory_id = request.POST.get("subcategory")
        product.price = request.POST.get("price")
        product.old_price = request.POST.get("old_price") or None
        product.stock = request.POST.get("stock")
        product.description = request.POST.get("description")

        product.status = bool(request.POST.get("status"))
        product.is_signature_collection = bool(request.POST.get("is_signature_collection"))
        product.is_featured = bool(request.POST.get("is_featured"))
        product.is_best_seller = bool(request.POST.get("is_best_seller"))

        product.additional_info = additional_info

        for i in range(1, 6):
            image = request.FILES.get(f"image{i}")
            if image:
                setattr(product, f"image{i}", image)

        product.save()
        product.sizes.set(request.POST.getlist("sizes"))

        messages.success(request, "Product updated successfully")
        return redirect("product_list")

    return render(request, "edit_product.html", {
        "product": product,
        "subcategories": subcategories,
        "sizes": sizes,
        "additional_info_json": additional_info_json,
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
def add_color(request):
    products = Product.objects.all()

    if request.method == "POST":
        product_id = request.POST.get("product")
        name = request.POST.get("name")
        hex_code = request.POST.get("hex_code")
        print(product_id, name, hex_code)

        if not product_id or not name or not hex_code:
            messages.error(request, "All fields are required.")
            return redirect("add_color")

        ProductColor.objects.create(
            product_id=product_id,
            name=name,
            hex_code=hex_code
        )

        messages.success(request, "Color added successfully.")
        return redirect("color_list")

    return render(request, "add_color.html", {
        "products": products
    })

@staff_member_required
def color_list(request):
    colors = ProductColor.objects.select_related("product").all()
    return render(request, "color_list.html", {
        "colors": colors
    })
@staff_member_required
def edit_color(request, id):
    color = get_object_or_404(ProductColor, id=id)
    products = Product.objects.all()

    if request.method == "POST":
        color.product_id = request.POST.get("product")
        color.name = request.POST.get("name")
        color.hex_code = request.POST.get("hex_code")
        color.save()

        messages.success(request, "Color updated successfully.")
        return redirect("color_list")

    return render(request, "edit_color.html", {
        "color": color,
        "products": products
    })
@staff_member_required
def delete_color(request, id):
    color = get_object_or_404(ProductColor, id=id)
    color.delete()
    messages.success(request, "Color deleted.")
    return redirect("color_list")


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





from django.shortcuts import render
from django.db.models import Avg, Count
from .models import Product, Review

def product_detail(request, slug):
    product = Product.objects.filter(slug=slug).first()

    if product:
        colors = product.colors.all()
        sizes = product.sizes.all().order_by('order')

        # All reviews
        reviews = Review.objects.filter(product=product).order_by('-id')

        # First 3 reviews
        first_three_reviews = reviews[:3]

        # Remaining reviews
        remaining_reviews = reviews[3:]

        # Average rating
        average_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        total_reviews = reviews.count()

        # Rating breakdown
        rating_counts = reviews.values('rating').annotate(count=Count('rating'))
        rating_dict = {i: 0 for i in range(1, 6)}
        for item in rating_counts:
            rating_dict[item['rating']] = item['count']

        rating_percent = {}
        for i in range(1, 6):
            if total_reviews > 0:
                rating_percent[i] = round((rating_dict[i] / total_reviews) * 100)
            else:
                rating_percent[i] = 0

        # Related products using subcategory
        related_products = Product.objects.filter(
            subcategory=product.subcategory
        ).exclude(id=product.id)[:4]

    else:
        colors = []
        sizes = []
        reviews = []
        first_three_reviews = []
        remaining_reviews = []
        average_rating = 0
        total_reviews = 0
        rating_percent = {i: 0 for i in range(1, 6)}
        related_products = []

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
    })


def register(request):
    return render(request,'register.html')

def reg_post(request):
    name=request.POST['name']
    email=request.POST['email']
    password=request.POST['password']
    phone=request.POST['phone']
    user=User.objects.create_user(  username=email,email=email,password=password,first_name=name )
    gp=Group.objects.get(name='registration')
    user.groups.add(gp)
    user.save()
    send_mail(
    subject="Account Created Successfully",
    message=(
        "Dear Customer,\n\n"
        "Welcome to our eCommerce platform!\n\n"
        "Your account has been created successfully and you can now start shopping with us.\n\n"
        "Use your registered email address to log in and explore our wide range of products, exclusive offers, and fast checkout experience.\n\n"
        "If you need any assistance, feel free to contact our support team.\n\n"
        "Happy Shopping!\n"
        "Regards,\n"
        "eCommerce Support Team"
    ),from_email=settings.EMAIL_HOST_USER,recipient_list=[email],)
    database=Registration()
    database.user_name=name
    database.email=email
    database.phone=phone
    database.password=password
    database.authuser=user
    database.save()
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

    # Name validation
    if name and (len(name) < 3 or not name.replace(" ", "").isalpha()):
        data['name_error'] = 'Name must be at least 3 letters and contain only alphabetic characters'

    # Email validation
    if email and User.objects.filter(username=email).exists():
        data['email_error'] = 'Email already exists'

    # Phone validation
    if phone:
        if not phone.isdigit():
            data['phone_error'] = 'Phone must contain only numbers'
        elif len(phone) != 10:
            data['phone_error'] = 'Phone must be 10 digits'
        elif Registration.objects.filter(phone=phone).exists():
            data['phone_error'] = 'Phone number already registered'

    # Password validation
    if password:
        if len(password) < 6:
            data['password_error'] = 'Password must be at least 6 characters'
        elif password.isdigit():
            data['password_error'] = 'Password cannot be only numbers'

    return JsonResponse(data)


def user_login(request):
    return render(request,'login.html')
def login_post(request):
    login_input = request.POST.get('name', '').strip()
    password = request.POST.get('password', '').strip()

    # Password validation
    if not password:
        messages.error(request, "Password is required")
        return redirect('user_login')

    if len(password) < 6:
        messages.error(request, "Password must be at least 6 characters")
        return redirect('user_login')

    if password.isdigit():
        messages.error(request, "Password cannot be only numbers")
        return redirect('user_login')

    # Identify user by email or username
    try:
        user_obj = User.objects.get(email=login_input)
        username = user_obj.username
    except User.DoesNotExist:
        username = login_input

    user = authenticate(request, username=username, password=password)

    if user is not None:
        login(request, user)

        if user.is_staff or user.is_superuser:
         return redirect("dashboard")

        elif user.groups.filter(name='registration').exists():
            return redirect('home')
        else:
            return redirect('user_login')
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
        

        # Validate rating
        if not rating:
            return JsonResponse({
                'status': 'error',
                'message': '⚠ Please select a rating.'
            })

        registration, created = Registration.objects.get_or_create(authuser=user)

        Review.objects.create(
            name=user.get_full_name() if user.get_full_name() else user.username,
            email=user.email,
            rating=int(rating),
            message=comment,
            product=product,
            registration=registration
        )

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
        return JsonResponse({"success": False, "message": "Please login to add items to your cart."})

    product = get_object_or_404(Product, id=product_id)
    size_id = request.POST.get("size")
    color_id = request.POST.get("color")
    quantity = int(request.POST.get("quantity", 1))

    #  COLOR validation
    if product.colors.exists():
        if not color_id:
            return JsonResponse({"success": False, "message": "Please select a color."})
        color = get_object_or_404(ProductColor, id=color_id)
    else:
        color = None

    #  SIZE validation
    if product.sizes.exists():
        if not size_id:
            return JsonResponse({"success": False, "message": "Please select a size."})
        size = get_object_or_404(Size, id=size_id)
    else:
        size = None

    #  Stock validation
    if quantity > product.stock:
        return JsonResponse({"success": False, "message": f"Only {product.stock} item(s) available."})

    registration = get_object_or_404(Registration, authuser=request.user)
    cart, _ = Cart.objects.get_or_create(registration=registration)

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        color=color,
        size=size,
        defaults={"quantity": quantity, "price": product.price}
    )

    if not created:
        if item.quantity + quantity > product.stock:
            return JsonResponse({"success": False, "message": f"Only {product.stock} item(s) available."})
        item.quantity += quantity
        item.save()

    return JsonResponse({"success": True, "message": "Product added to cart!"})


@login_required(login_url='user_login')
def cart_page(request):
    registration = get_object_or_404(Registration, authuser=request.user)
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
                    coupon = Coupon.objects.get(code__iexact=coupon_code, active=True)

                    if coupon.expiry_date and coupon.expiry_date < date.today():
                        cart.coupon_discount = Decimal("0.00")
                        message = "Coupon expired"
                    else:
                        cart.coupon_code = coupon.code
                        cart.coupon_discount = coupon.discount_amount
                        message = "Coupon applied!"

                except Coupon.DoesNotExist:
                    cart.coupon_discount = Decimal("0.00")
                    message = "Invalid coupon"

                cart.save()

    # ✅ THIS LINE STORES VALUES IN DB
    cart.update_totals()

    return render(request, "cart.html", {
        "cart": cart,
        "items": items,
        "has_items": has_items,

        # existing variables (no break)
        "subtotal": cart.subtotal(),
        "total": cart.total(),

        # DB values (optional)
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

    items = cart.items.all()
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


from django.db import transaction

@login_required
@transaction.atomic
def checkout_post(request):
    if request.method != "POST":
        return redirect("home")

    registration = get_object_or_404(Registration, authuser=request.user)
    cart = get_object_or_404(Cart, registration=registration)
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if not cart.items.exists():
        messages.warning(request, "Your cart is empty")
        return redirect("cart_page")

    # Billing details
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

    # ==========================
    # STOCK CHECK (FOR ALL)
    # ==========================
    for item in cart.items.select_related("product"):
        if item.quantity > item.product.stock:
            messages.error(
                request,
                f"{item.product.name} only {item.product.stock} item(s) available."
            )
            return redirect("cart_page")

    # ==========================
    # CASH ON DELIVERY
    # ==========================
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

        for item in cart.items.select_related("product"):
            product = item.product

            # 🔥 Reduce stock
            product.stock -= item.quantity
            product.save()

            OrderItem.objects.create(
                order=order,
                product=product,
                color=item.color,
                size=item.size,
                quantity=item.quantity,
                price=item.price
            )

        # Clear cart
        cart.items.all().delete()
        cart.coupon_code = None
        cart.coupon_discount = 0
        cart.save()

        return redirect("cash_on_delivery_success", order_id=order.id)

    # ==========================
    # RAZORPAY FLOW
    # ==========================
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

    for item in cart.items.select_related("product"):
        OrderItem.objects.create(
            order=order,
            product=item.product,
            color=item.color,
            size=item.size,
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

    # Phone
    if phone:
        if not phone.isdigit():
            data["phone_error"] = "Phone must contain only numbers"
        elif len(phone) != 10:
            data["phone_error"] = "Phone must be 10 digits"

    # Pincode
    if pincode:
        if not pincode.isdigit():
            data["pincode_error"] = "Pincode must contain only numbers"
        elif len(pincode) != 6:
            data["pincode_error"] = "Pincode must be 6 digits"

    # State
    if state in ["", "Select a state"]:
        data["state_error"] = "Please select a valid state"

    # Town
    if town and len(town) < 2:
        data["town_error"] = "Enter a valid town/city"

    # Address
    if address and len(address) < 10:
        data["address_error"] = "Address is too short"

    # ✅ Land Mark
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

        # 🔹 Reduce product stock
        for item in order.items.all():
            product = item.product
            if product.stock >= item.quantity:
                product.stock -= item.quantity
                product.save()

        # 🔹 Clear cart
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
    # Get or create profile for logged-in user
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        profile.phone = request.POST.get("phone", "").strip()
        profile.address = request.POST.get("address", "").strip()

        # Handle profile image
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



@login_required(login_url='user_login')
def dashboard(request):
    today = now().date()

    orders = Order.objects.all().order_by('-created_at')

    # Revenue calculations
    paid_orders = orders.filter(payment_status=True)

    total_revenue = paid_orders.aggregate(
        total=Sum("total")
    )["total"] or 0

    today_revenue = paid_orders.filter(
        created_at__date=today
    ).aggregate(
        total=Sum("total")
    )["total"] or 0

    context = {
        "total_revenue": total_revenue,
        "today_revenue": today_revenue,

        "total_orders": orders.count(),
        "paid_orders": paid_orders.count(),
        "pending_orders": orders.filter(payment_status=False).count(),

        "total_customers": Registration.objects.count(),
        "total_products": Product.objects.count(),

        "orders": orders,
    }

    return render(request, "dashboard.html", context)

    return render(request, "dashboard.html", context)
def order_list(request):
    orders = Order.objects.all().order_by('-created_at')

    return render(request, 'orders_view.html', {
        'orders': orders,
        'title': 'All Orders'
    })

@login_required(login_url='user_login')
def paid_orders(request):
    orders = Order.objects.filter(payment_status=True).order_by('-created_at')
    return render(request, 'orders_view.html', {
        'orders': orders,
        'title': 'Paid Orders'
    })


@login_required(login_url='user_login')
def pending_orders(request):
    orders = Order.objects.filter(payment_status=False).order_by('-created_at')
    return render(request, 'orders_view.html', {
        'orders': orders,
        'title': 'Pending Orders'
    })

def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "order_detail.html", {"order": order})



@login_required(login_url='user_login')
def mark_order_completed(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Mark delivered
    order.is_delivered = True

    # If COD → payment received on delivery
    if order.payment_method == "cod":
        order.payment_status = True

    order.save()

    return redirect('dashboard')


def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if not order.is_delivered and not order.is_cancelled:

        # 🔥 Restore stock
        for item in order.items.all():
            product = item.product
            product.stock = F('stock') + item.quantity
            product.save(update_fields=["stock"])

        order.is_cancelled = True
        order.save(update_fields=["is_cancelled"])

        messages.success(request, "Order cancelled and stock restored.")

    return redirect("order_detail", order_id=order.id)



@login_required(login_url='user_login')
def customer_list(request):
    customers = Registration.objects.all().order_by('-id')
    return render(request, 'customers_view.html', {
        'customers': customers
    })
def shipping_address_list(request):
    # Get all orders
    orders = Order.objects.all().order_by('-created_at')
    
    context = {
        'title': 'Shipping Address List',
        'orders': orders
    }
    return render(request, 'shipping_address_list.html', context)



def article_list(request):
    articles = Article.objects.all().order_by('-posted_on')
    return render(request, 'article_list.html', {'articles': articles})


def add_article(request):
    if request.method == "POST":
        title = request.POST.get('title')
        content = request.POST.get('content')
        image = request.FILES.get('image')

        Article.objects.create(
            title=title,
            content=content,
            image=image
        )

        messages.success(request, "Article Added Successfully")
        return redirect('article_list')

    return render(request, 'add_article.html')


def edit_article(request, slug):
    article = get_object_or_404(Article, slug=slug)

    if request.method == "POST":
        article.title = request.POST.get('title')
        article.content = request.POST.get('content')

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
