from django.shortcuts import render
from django.core.paginator import Paginator
from ..models import Product, Category

def home(request):
    products_list = Product.objects.all().order_by('-id')
    categories = Category.objects.all()
    
    # Filter by category
    category_id = request.GET.get('category')
    if category_id:
        products_list = products_list.filter(category_id=category_id)
    
    # Pagination with 12 products per page
    paginator = Paginator(products_list, per_page=12)
    page_number = request.GET.get('page', 1)
    products = paginator.get_page(page_number)
    
    context = {
        'products': products,
        'categories': categories,
        'total_products': products_list.count(),
        'total_pages': paginator.num_pages,
        'current_page': int(page_number),
    }
    
    return render(request, 'app/home.html', context)