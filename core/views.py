from django.shortcuts import render


def home(request):
    return render(request, "core/home.html", {"name": "Romaan_Ali"})


def about(request):
    return render(request, "core/about.html")