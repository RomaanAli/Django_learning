from django.http import HttpResponse
from django.views import View


class HomeView(View):

    def get(self, request):
        return HttpResponse(
            "Welcome (---GET---) to our E-Learning Website!"
        )

    def post(self, request):
        return HttpResponse(
            "Welcome (---POST---) to our E-Learning Website!"
        )