from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import EmailVerification
from .serializers import MeUserSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """Return the current user's profile with the exact legacy response shape.

    The hard requirement is that GET /api/me/ returns exactly these four keys:
    {"id", "username", "email", "email_verified"}.
    """
    user = request.user
    try:
        email_verified = user.email_verification.is_verified
    except EmailVerification.DoesNotExist:
        email_verified = False

    return Response(
        {
            "id": user.pk,
            "username": user.username,
            "email": user.email,
            "email_verified": email_verified,
        }
    )


class MeSerializerView(generics.RetrieveAPIView):
    """Serializer-based view for GET /api/me/.

    The dedicated MeUserSerializer guarantees the response has exactly the
    four required keys.  The full UserSerializer would add first_name,
    last_name and role, which would break the hard contract.
    """

    queryset = None  # set in the view below
    serializer_class = MeUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

