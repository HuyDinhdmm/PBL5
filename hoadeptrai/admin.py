from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Customer, Category, Product, Promotion, Order

class CustomerAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'phone_number')
    list_filter = ('role', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role', 'phone_number', 'address', 'loyalty_points')}),
    )

admin.site.register(Customer, CustomerAdmin)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Promotion)
admin.site.register(Order)
