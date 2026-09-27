from django.views.generic import TemplateView


class HomeView(TemplateView):
    """Render the site's home page."""

    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["name"] = "Romaan_Ali"
        return context


class AboutView(TemplateView):
    """Render the site's about page."""

    template_name = "core/about.html"