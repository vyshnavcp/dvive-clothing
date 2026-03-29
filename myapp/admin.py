from django.contrib import admin
from .models import *
from .models import Article

from unfold.admin import ModelAdmin

from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.admin import register
from django.contrib.auth.models import User
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from .models import Product, Category, SubCategory, Size


admin.site.unregister(User)
@register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


# ================= BASIC MODELS =================
@admin.register(Contact)
class ContactAdmin(ModelAdmin):
    list_display = ("name", "email", "phone", "created_at")
    search_fields = ("name", "email")


@admin.register(HomeBanner)
class HomeBannerAdmin(ModelAdmin):
    list_display = ("title_line1", "title_line2", "is_active")
    list_filter = ("is_active",)


@admin.register(Registration)
class RegistrationAdmin(ModelAdmin):
    list_display = ("user_name", "email", "phone", "created_at")
    search_fields = ("user_name", "email")


# ================= CMS =================
@admin.register(Article)
class ArticleAdmin(ModelAdmin):
    list_display = ('title', 'posted_on')
    search_fields = ('title', 'content')
    readonly_fields = ('slug',)


@admin.register(TermsCondition)
class TermsAdmin(ModelAdmin):
    list_display = ("updated_at",)


@admin.register(PrivacyPolicy)
class PrivacyAdmin(ModelAdmin):
    list_display = ("updated_at",)


@admin.register(FAQ)
class FAQAdmin(ModelAdmin):
    list_display = ("question", "created_at")
    search_fields = ("question",)


# ================= CATEGORY =================
@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ('name', 'slug')


@admin.register(SubCategory)
class SubCategoryAdmin(ModelAdmin):
    list_display = ('name', 'category', 'slug')
    readonly_fields = ('slug',)
    list_filter = ('category',)
    search_fields = ('name',)


# ================= PRODUCT =================
@admin.register(Size)
class SizeAdmin(ModelAdmin):
    list_display = ('name', 'order')
    ordering = ('order',)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


class ProductColorInline(admin.TabularInline):
    model = ProductColor
    extra = 1


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = (
        'name', 'brand', 'product_code', 'subcategory',
        'price', 'stock', 'status',
        'is_featured', 'is_best_seller'
    )

    list_filter = (
        'subcategory', 'status',
        'is_featured', 'is_best_seller'
    )

    search_fields = ('name', 'brand', 'product_code')
    readonly_fields = ('created_at', 'updated_at', 'style_type_display', 'material_type_display')

    inlines = [ProductColorInline, ProductVariantInline]

    fieldsets = (
        ('Relations', {
            'fields': ('subcategory',)
        }),
        ('Basic Info', {
            'fields': ('name', 'brand', 'product_code', 'slug', 'description', 'additional_info')
        }),
        ('Pricing', {
            'fields': ('price', 'old_price', 'cost_price', 'stock')
        }),
        ('Flags', {
            'fields': ('status', 'is_signature_collection', 'is_featured', 'is_best_seller')
        }),
        ('Images', {
            'fields': ('image1', 'image2', 'image3', 'image4', 'image5')
        }),
        ('Extra Info', {
            'fields': ('style_type_display', 'material_type_display')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def style_type_display(self, obj):
        return ", ".join(obj.style_type or [])
    style_type_display.short_description = "Style Types"

    def material_type_display(self, obj):
        return ", ".join(obj.material_type or [])
    material_type_display.short_description = "Material Types"


# ================= REVIEW =================
@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ("product", "email", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("email", "product__name")


# ================= CART =================
class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(ModelAdmin):
    list_display = ("registration", "subtotal_amount", "total_amount", "created_at")
    inlines = [CartItemInline]


# ================= COUPON =================
@admin.register(Coupon)
class CouponAdmin(ModelAdmin):
    list_display = ("code", "discount_amount", "active", "min_cart_value", "expiry_date")
    list_filter = ("active",)
    search_fields = ("code",)


# ================= ORDER =================
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = (
        "id", "first_name", "phone", "total",
        "payment_method", "payment_status",
        "is_completed", "is_delivered", "created_at"
    )

    list_filter = (
        "payment_method", "payment_status",
        "is_completed", "is_delivered"
    )

    search_fields = ("first_name", "phone", "reference")
    inlines = [OrderItemInline]


# ================= USER PROFILE =================
@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = ("user", "phone", "town", "state")