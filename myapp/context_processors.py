from .models import Cart, Category,SubCategory


def cart_count(request):
    # if user is logged in
    if request.user.is_authenticated:
        try:
            # get user's cart
            cart = Cart.objects.get(registration__authuser=request.user)
            # count cart items
            count = cart.items.count()
        except Cart.DoesNotExist:
            count = 0
    else:
        count = 0

    return {
        'cart_item_count': count
    }
def footer_categories(request):
    """
    Adds categories to all templates for the footer
    """
    categories = SubCategory.objects.all()
    return {
        'footer_categories': categories
    }
def navbar_categories(request):
    """
    Adds categories with subcategories for navbar mega menu
    """
    categories = Category.objects.prefetch_related("subcategories").all()
    return {
        "nav_categories": categories
    }