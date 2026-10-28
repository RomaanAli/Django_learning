from rest_framework import serializers

from payments.models import Payment


class CourseMiniSerializer(serializers.Serializer):
    """Tiny nested serializer for the payment's course.

    Only id and title are exposed; no instructor or other sensitive fields.
    """

    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)


class PaymentSerializer(serializers.ModelSerializer):
    """Read-only payment serializer.

    Every field is read-only.  Payments are created only by the existing
    Stripe flow; the API must never allow create/update/delete.
    """

    course = CourseMiniSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "course",
            "amount",
            "currency",
            "status",
            "created_at",
        ]
        read_only_fields = fields
