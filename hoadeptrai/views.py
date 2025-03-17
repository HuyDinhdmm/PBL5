from django.shortcuts import render
from django.http import HttpResponse


def home(request):
    return render(request, 'app/home.html') 
def cart(request):
    context={}
    return render(request, 'app/cart.html',context)
def checkout(request):
    context={}
    return render(request, 'app/checkout.html',context)