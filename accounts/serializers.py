from rest_framework import serializers

from .models import User, EmailVerification


class InstructorMiniSerializer(serializers.Serializer):

    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)


class UserSerializer(serializers.ModelSerializer):

    role = serializers.ReadOnlyField()
    email_verified = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "email_verified",
        ]
        read_only_fields = ["role"]

    def get_email_verified(self, obj):
        try:
            return obj.email_verification.is_verified
        except EmailVerification.DoesNotExist:
            return False


class MeUserSerializer(serializers.Serializer):

    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    email_verified = serializers.SerializerMethodField()

    def get_email_verified(self, obj):
        try:
            return obj.email_verification.is_verified
        except EmailVerification.DoesNotExist:
            return False
