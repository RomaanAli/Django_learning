from django.http import HttpResponse


def home(request):
    return HttpResponse("Welcome to our E-Learning Website!")

def courses(request):
    return HttpResponse("Here are all the courses.")

def about(request):
    return HttpResponse("About our E-Learning Website.")

def contact(request):
    return HttpResponse("Contact us.")

def student(request):
    return HttpResponse("Student Dashboard")