from django.contrib import admin
from .models import Product, Order, Profile, Category, CourierProfile

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'id')
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'address')
    search_fields = ('user__username', 'address')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category', 'unit_type', 'instock', 'is_in_stock')
    list_editable = ('price', 'unit_type', 'instock', 'category') # Change stock,price and categories directly from the list!
    search_fields = ('name', 'category__name')
    list_filter = ('category', 'unit_type')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # Search the 'address' field on the Order itself
    list_display = ('ref', 'user', 'payment_method', 'get_display_address', 'amount', 'status', 'verified')
    search_fields = ('ref', 'user__username', 'address') # Search the snapshot address
    list_filter = ('payment_method', 'status', 'verified', 'created_at')
    
    def get_display_address(self, obj):
        # 1. Use the snapshot address on the order first
        # 2. Fallback to profile only if order.address is missing
        if obj.address:
            return obj.address
        return obj.user.profile.address if hasattr(obj.user, 'profile') else "No Address"
    
    get_display_address.short_description = 'Delivery Location'


@admin.register(CourierProfile)
class CourierProfileAdmin(admin.ModelAdmin):
    # Display the username, their halls, and if they are active
    list_display = ('user', 'location_1', 'location_2', 'get_email')
    search_fields = ('user__username', 'location_1', 'location_2')
    list_filter = ('location_1', 'location_2')
    
    # This allows you to see the rider's email directly in the list
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Rider Email'