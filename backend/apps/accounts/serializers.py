from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.services import record_event

from .models import User
from .services import active_roles, user_has_valid_habilitation
from .validators import normalize_phone


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            phone = normalize_phone(attrs["phone"])
        except ValidationError:
            phone = attrs["phone"]
        user = authenticate(phone=phone, password=attrs["password"])
        if not user or not user.is_active:
            record_event("login_failed", details={"phone": phone})
            raise serializers.ValidationError("Identifiants invalides.")
        record_event("login_succeeded", actor_user=user, entity_id=user.id)
        refresh = RefreshToken.for_user(user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class UserMeSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    has_valid_habilitation = serializers.SerializerMethodField()
    accessible_centers = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "phone", "full_name", "language", "roles", "has_valid_habilitation", "accessible_centers")

    def get_roles(self, obj):
        return [{"code": role.code, "label_fr": role.label_fr} for role in active_roles(obj)]

    def get_has_valid_habilitation(self, obj):
        return user_has_valid_habilitation(obj)

    def get_accessible_centers(self, obj):
        from apps.identity.models import Center

        return list(
            Center.objects.filter(
                centermember__user=obj,
                centermember__starts_at__lte=timezone.now(),
            ).filter(
                Q(centermember__ends_at__isnull=True)
                | Q(centermember__ends_at__gt=timezone.now())
            ).values("id", "name", "center_type")
        )


class RefreshSerializer(TokenRefreshSerializer):
    pass
