import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import StateModel, UUIDModel

from .validators import normalize_phone, validate_phone


class UserManager(BaseUserManager):
    def get_by_natural_key(self, phone):
        # Connexion : "07 07 07 07 07" retrouve le compte "+2250707070707".
        try:
            phone = normalize_phone(phone)
        except ValidationError:
            pass
        return super().get_by_natural_key(phone)

    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("Le numéro de téléphone est obligatoire.")
        user = self.model(phone=normalize_phone(phone), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=20, unique=True, validators=[validate_phone])
    full_name = models.CharField(max_length=120)
    language = models.CharField(max_length=5, default="fr")
    is_active = models.BooleanField(default=True)
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_simulated = models.BooleanField(default=False)
    objects = UserManager()
    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "app_user"

    def __str__(self):
        return self.phone


class Organization(StateModel):
    name = models.CharField(max_length=160)
    kind = models.CharField(max_length=20)
    zone = models.ForeignKey("geo.Zone", null=True, blank=True, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "organization"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    kind__in=("veterinary_service", "cooperative", "market", "abattoir", "authority", "other")
                ),
                name="chk_organization_kind",
            )
        ]


class Role(UUIDModel):
    code = models.CharField(max_length=30, unique=True)
    label_fr = models.CharField(max_length=80)
    description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "role"


class Membership(UUIDModel):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    role = models.ForeignKey(Role, on_delete=models.PROTECT)
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.PROTECT)
    zone = models.ForeignKey("geo.Zone", null=True, blank=True, on_delete=models.PROTECT)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "membership"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_at__isnull=True) | models.Q(ends_at__gt=models.F("starts_at")),
                name="chk_membership_ends_after_start",
            ),
            models.UniqueConstraint(
                fields=("user", "role", "organization"),
                condition=models.Q(ends_at__isnull=True),
                nulls_distinct=False,
                name="uniq_membership_active_role",
            ),
        ]


class Habilitation(StateModel):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    kind = models.CharField(max_length=20)
    reference_number = models.CharField(max_length=60)
    valid_from = models.DateField()
    valid_to = models.DateField()
    status = models.CharField(max_length=12)
    verified_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.PROTECT, related_name="verified_habilitations"
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "habilitation"
        constraints = [
            models.CheckConstraint(condition=models.Q(kind__in=("vet_order", "mandate_state", "other")), name="chk_habilitation_kind"),
            models.CheckConstraint(condition=models.Q(status__in=("pending", "verified", "revoked", "expired")), name="chk_habilitation_status"),
            models.CheckConstraint(condition=models.Q(valid_to__gte=models.F("valid_from")), name="chk_habilitation_valid_dates"),
            models.CheckConstraint(condition=models.Q(verified_by__isnull=True) | ~models.Q(verified_by=models.F("user")), name="chk_habilitation_verified_by_other"),
        ]


class Mandate(UUIDModel):
    agent_user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="received_mandates")
    granted_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="granted_mandates")
    scope = models.CharField(max_length=20)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mandate"
        constraints = [models.CheckConstraint(condition=models.Q(scope__in=("declare", "move", "all")), name="chk_mandate_scope")]


class Device(UUIDModel):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    label = models.CharField(max_length=60, null=True, blank=True)
    platform = models.CharField(max_length=10)
    registered_at = models.DateTimeField()
    last_seen_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "device"
        constraints = [models.CheckConstraint(condition=models.Q(platform__in=("android", "ios", "web", "other")), name="chk_device_platform")]
