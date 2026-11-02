from django.urls import path
from chatbot import views

app_name = "chatbot"

urlpatterns = [
    path("ask/", views.ask_chatbot, name="ask"),
    path("rebuild-index/", views.rebuild_index, name="rebuild_index"),
]

