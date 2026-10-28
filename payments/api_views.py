from rest_framework import generics, permissions

from .serializers import PaymentSerializer


class PaymentListCreateView(generics.ListAPIView):

    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            self.request.user.payments.select_related("course")
            .order_by("-created_at")
        )


class PaymentDetailView(generics.RetrieveAPIView):
    """Read-only detail of a single payment.

    Queryset restricted to the requesting user's payments.  Another user's
    payment returns 404.
    """

    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.payments.select_related("course")
