from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import EmailVerification


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    
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
