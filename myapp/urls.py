from django.urls import path, reverse_lazy
from . import views
from django.conf import settings
from django.contrib.auth import views as auth_views
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('product/',views.product,name='product'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('product/subcategory/<slug:slug>/', views.product, name='filter_by_subcategory'),
    path('product/<slug:slug>/review/',views.review_post,name='submit_review'),
    path('blog/',views.blog,name='blog'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('register/',views.register,name='register'),
    path('reg_post/',views.reg_post,name='reg_post'),
    path('user_login/', views.user_login, name='user_login'),
    path('login_post/',views.login_post,name='login_post'),
    path('logout/', views.user_logout, name='user_logout'),
    path('ajax/validate-register/', views.ajax_validate_register, name='ajax_validate_register'),  
    # Send reset link
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='password_reset.html'
        ),
        name='password_reset'
    ),

    # Email sent confirmation
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='password_reset_done.html'
        ),
        name='password_reset_done'
    ),

    # Reset link (token + uid)
    path(
    'reset/<uidb64>/<token>/',
    auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete')
    ),
    name='password_reset_confirm'
),

    # Password successfully changed
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),
    path("add-to-cart/<int:product_id>/",views.add_to_cart, name="add_to_cart"),
    path("cart/",views. cart_page, name="cart_page"),
    path("cart/update/<int:item_id>/",views. update_cart, name="update_cart"),
    path("cart/remove/<int:item_id>/",views. remove_cart_item, name="remove_cart_item"),
    path("cart/empty/", views.empty_cart, name="empty_cart"),
    path('checkout/',views.checkout,name='checkout'),
    path("cart/change-quantity/<int:item_id>/",views.change_cart_quantity,name="change_cart_quantity"),
    path('checkout/', views.checkout, name='checkout'),  # Page with billing form
    path('checkout/post/', views.checkout_post, name='checkout_post'),  # Handle form, create order, Razorpay
    path('payment/success/', views.payment_success_post, name='payment_success_post'),  # Razorpay callback  
    path('order/success/', views.order_success, name='order_success'),
    path("order/cash-on-delivery/<int:order_id>/",views.cash_on_delivery_success,name="cash_on_delivery_success"),
    path("ajax/validate-checkout/", views.ajax_validate_checkout, name="ajax_validate_checkout"),
    path("profile/", views.profile, name="profile"),
    path("my-orders/", views.my_orders, name="my_orders"),
    path("ajax/shipping-charge/", views.ajax_shipping_charge, name="ajax_shipping_charge"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path('order/complete/<int:order_id>/', views.mark_order_completed, name='mark_order_completed'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/paid/', views.paid_orders, name='paid_orders'),
    path('orders/pending/', views.pending_orders, name='pending_orders'),
    path("order/<int:order_id>/",views.order_detail, name="order_detail"),
    path("order/<int:order_id>/complete/", views.mark_order_completed, name="mark_order_completed"),
    path("cancel-order/<int:order_id>/", views.cancel_order, name="cancel_order"),
    path('shipping-address/', views.shipping_address_list, name='shipping_address_list'),
    path('customers/', views.customer_list, name='customer_list'),
    path("dashboard/category/add/", views.add_category, name="add_category"),
    path("dashboard/categories/", views.category_list, name="category_list"),
    path("dashboard/category/edit/<int:id>/", views.edit_category, name="edit_category"),
    path("dashboard/category/delete/<int:id>/", views.delete_category, name="delete_category"),
    path("dashboard/subcategory/add/", views.add_subcategory, name="add_subcategory"),
    path("dashboard/subcategories/", views.subcategory_list, name="subcategory_list"),
    path("dashboard/subcategory/edit/<int:id>/", views.edit_subcategory, name="edit_subcategory"),
    path("dashboard/subcategory/delete/<int:id>/", views.delete_subcategory, name="delete_subcategory"),
    path("dashboard/product/add/", views.add_product, name="add_product"),
    path("dashboard/products/", views.product_list, name="product_list"),
    path("dashboard/product/edit/<slug:slug>/",views.edit_product,name="edit_product"),
    path("dashboard/product/delete/<slug:slug>/",views.delete_product,name="delete_product"),
    path("dashboard/size/add/", views.add_size, name="add_size"),
    path("dashboard/size/", views.size_list, name="size_list"),
    path("dashboard/size/edit/<int:id>/", views.edit_size, name="edit_size"),
    path("dashboard/size/delete/<int:id>/", views.delete_size, name="delete_size"),
    path("dashboard/color/add/", views.add_color, name="add_color"),
    path("dashboard/color/", views.color_list, name="color_list"),
    path("dashboard/color/edit/<int:id>/", views.edit_color, name="edit_color"),
    path("dashboard/color/delete/<int:id>/", views.delete_color, name="delete_color"),
    path("dashboard/coupon/add/", views.add_coupon, name="add_coupon"),
    path("dashboard/coupon/", views.coupon_list, name="coupon_list"),
    path("dashboard/coupon/edit/<int:id>/", views.edit_coupon, name="edit_coupon"),
    path("dashboard/coupon/delete/<int:id>/", views.delete_coupon, name="delete_coupon"),
    
    



    


    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
