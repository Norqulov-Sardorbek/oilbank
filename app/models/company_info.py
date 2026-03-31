import os.path
from django.db import models
from ckeditor.fields import RichTextField
from uuid import uuid4

from django.utils.text import slugify

from .log_connection import SyncSoftDeleteMixin
from app.utils.utils import OdooSync
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


def branch_upload_to(instance, filename):
    exc = filename.split(".")[-1]
    filename = f"{uuid4()}.{exc}"
    return os.path.join("branches", filename)


def banner_upload_to(instance, filename):
    exc = filename.split(".")[-1]
    filename = f"{uuid4()}.{exc}"
    return os.path.join("banner", filename)


def document_upload_to(instance, filename):
    exc = filename.split(".")[-1]
    filename = f"{uuid4()}.{exc}"
    return os.path.join("documents", filename)


def company_benefit_upload_to(instance, filename):
    exc = filename.split(".")[-1]
    filename = f"{uuid4()}.{exc}"
    return os.path.join("company-benefit", filename)


def company_logo_upload_to(instance, filename):
    exc = filename.split(".")[-1]
    filename = f"{uuid4()}.{exc}"
    return os.path.join("company-logo", filename)


def comment_avatar_upload_to(instance, filename):
    exc = filename.split(".")[-1]
    filename = f"{uuid4()}.{exc}"
    return os.path.join("comment-avatar", filename)


class Branch(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(max_length=255)
    name = models.CharField(max_length=400, unique=True)
    name_ru = models.CharField(max_length=400, blank=True, null=True)
    name_uz = models.CharField(max_length=400, blank=True, null=True)
    image = models.ImageField(upload_to=branch_upload_to, blank=True, null=True)
    parent_branch = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True
    )

    branch_type = models.CharField(
        max_length=50,
        choices=[
            ("REGULAR", "Regular Branch"),
            ("MAIN", "Main Branch"),
            ("ONLINE", "Online Branch"),
        ],
        default="REGULAR",
        help_text="Type of the branch (e.g., Regular, Main, Online)",
    )

    city = models.CharField(null=True,blank=True)
    street=models.CharField(null=True,blank=True)
    phone=models.CharField(null=True,blank=True)

    contacts = RichTextField()
    order_expiration_days = models.PositiveIntegerField(
        null=True, blank=True, help_text="Order expiration time (in days)"
    )
    vat = models.CharField(max_length=50, default="310516499")
    longitude = models.CharField(max_length=50, null=True, blank=True)
    latitude = models.CharField(max_length=50, null=True, blank=True)
    google_link = models.URLField(blank=True, null=True)
    yandex_link = models.URLField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_main = models.BooleanField(default=False, help_text="Indicates if this branch is the main branch of the company")

    def __str__(self):
        return self.name or "Unnamed Branch"

    def prepare_odoo_data(self):
        return OdooSync.prepare_branch_data(self)


class AboutUs(SyncSoftDeleteMixin):
    title = models.CharField(max_length=255)
    description = RichTextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class PrivacyPolicy(SyncSoftDeleteMixin):
    title_en = models.TextField(null=True, blank=True)
    title_uz = models.TextField(null=True, blank=True)
    title_ru = models.TextField(null=True, blank=True)
    description_en = RichTextField(null=True, blank=True)
    description_uz = RichTextField(null=True, blank=True)
    description_ru = RichTextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)

    def __str__(self):
        return self.title_en


class Contact(SyncSoftDeleteMixin):
    phone1 = models.CharField(max_length=20)
    phone2 = models.CharField(max_length=20, blank=True, null=True)
    email1 = models.EmailField()
    email2 = models.EmailField(blank=True, null=True)
    recrutement = models.URLField(blank=True,null=True)
    telegram = models.URLField(blank=True, null=True)
    instagram = models.URLField(blank=True, null=True)
    facebook = models.URLField(blank=True, null=True)
    telegram_bot = models.URLField(blank=True, null=True)
    address = models.TextField()
    yandex_link = models.URLField(blank=True, null=True)
    google_link = models.URLField(blank=True, null=True)
    app_google_play_link = models.URLField(blank=True, null=True)
    app_app_store_link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.phone1} - {self.email1}"


class UserAgreement(SyncSoftDeleteMixin):
    title_en = models.TextField()
    title_uz = models.TextField()
    title_ru = models.TextField()
    description_en = RichTextField()
    description_uz = RichTextField()
    description_ru = RichTextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title_en


class FAQ(SyncSoftDeleteMixin):
    question_en = models.TextField(null=True, blank=True)
    question_uz = models.TextField(null=True, blank=True)
    question_ru = models.TextField(null=True, blank=True)
    answer_en = models.TextField(null=True, blank=True)
    answer_uz = models.TextField(null=True, blank=True)
    answer_ru = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order_number = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order_number"]

    def __str__(self):
        return self.question_en or "FAQ"


class SupportContact(SyncSoftDeleteMixin):
    phone = models.CharField(max_length=50)
    email = models.EmailField()
    support_chat_url = models.URLField(help_text="Link to support chat (e.g., Telegram)")

    def __str__(self):
        return self.phone


class Document(SyncSoftDeleteMixin):
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    file = models.FileField(upload_to=document_upload_to)
    file_name_uz = models.CharField(max_length=100, null=True, blank=True)
    file_name_ru = models.CharField(max_length=100, null=True, blank=True)
    file_name_en = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            (self.file_name_uz or "").strip()
            or (self.file_name_ru or "").strip()
            or (self.file_name_en or "").strip()
            or "No file name in any language"
        )


class CompanyBenefit(SyncSoftDeleteMixin):
    image = models.ImageField(
        upload_to=company_benefit_upload_to, blank=True, null=True
    )
    title_en = models.CharField(max_length=255, blank=True)
    title_ru = models.CharField(max_length=255, blank=True)
    title_uz = models.CharField(max_length=255, blank=True)
    description_en = models.TextField(blank=True)
    description_ru = models.TextField(blank=True)
    description_uz = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "CompanyBenefit"
        verbose_name_plural = "CompanyBenefit"

    def __str__(self):
        return self.title_en or self.title_ru or self.title_uz or "Untitled"


class CompanyComment(SyncSoftDeleteMixin):
    company_name = models.CharField(max_length=255)
    company_logo = models.ImageField(
        upload_to=company_logo_upload_to, null=True, blank=True
    )
    avatar = models.ImageField(
        upload_to=comment_avatar_upload_to, null=True, blank=True
    )

    full_name_en = models.CharField(max_length=255)
    full_name_uz = models.CharField(max_length=255)
    full_name_ru = models.CharField(max_length=255)

    comment_en = models.TextField(blank=True)
    comment_uz = models.TextField(blank=True)
    comment_ru = models.TextField(blank=True)

    position_en = models.CharField(max_length=100)
    position_uz = models.CharField(max_length=100)
    position_ru = models.CharField(max_length=100)

    def __str__(self):
        return self.company_name


class WebPageInfo(models.Model):
    title_en = models.CharField(max_length=255, blank=True, null=True)
    title_ru = models.CharField(max_length=255, blank=True, null=True)
    title_uz = models.CharField(max_length=255, blank=True, null=True)
    url_uz = models.URLField(blank=True, null=True)
    url_ru = models.URLField(blank=True, null=True)
    url_en = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.title_en or self.title_ru or self.title_uz or "Untitled"


class StaticPage(SyncSoftDeleteMixin):
    title_en = models.CharField(max_length=255)
    title_ru = models.CharField(max_length=255, blank=True, null=True)
    title_uz = models.CharField(max_length=255, blank=True, null=True)

    subtitle_en = models.CharField(max_length=255, blank=True, null=True)
    subtitle_ru = models.CharField(max_length=255, blank=True, null=True)
    subtitle_uz = models.CharField(max_length=255, blank=True, null=True)

    content_en = RichTextField(blank=True, null=True)
    content_ru = RichTextField(blank=True, null=True)
    content_uz = RichTextField(blank=True, null=True)

    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True)
    include_form = models.BooleanField(default=False)
    image = models.ImageField(upload_to="static_page/", null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug and self.title_en:
            base_slug = slugify(self.title_en)
            slug = base_slug
            counter = 1
            while StaticPage.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title_en


class RequestForm(SyncSoftDeleteMixin):
    SOURCE_CHOICES = [
        ("WEB", _("Web")),
        ("MOBILE", _("Mobile")),
        ("TG_MINI_APP", _("Telegram Mini App")),
    ]

    name = models.CharField(max_length=255)
    organization = models.CharField(max_length=255)
    phone = models.CharField(max_length=255)
    email = models.EmailField(null=True, blank=True)
    commentary = models.TextField(
        null=True, blank=True, help_text="Description of the request"
    )
    source = models.CharField(
        max_length=50, choices=SOURCE_CHOICES, default="WEB", help_text="Source of the request"
    )
    source_page = models.ForeignKey(
        "StaticPage", on_delete=models.SET_NULL, null=True, blank=True, related_name="request_forms"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return  f"{self.name} : {self.phone}"
    
    def prepare_odoo_data(self):
        return OdooSync.prepare_request_form_data(self)


class LandingPageBanner(SyncSoftDeleteMixin):
    image = models.ImageField(upload_to=banner_upload_to, null=True, blank=True)
    link = models.URLField(blank=True, null=True)
    order_number = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order_number"]

    def __str__(self):
        return self.link or "No link"