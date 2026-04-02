import json

from django.contrib import admin

from .models import Story
from .models.log_connection import OdooConnectorLog
from .models.order import (
    Order,
    OrderItem,
    OrderRating,
    Basket,
    BasketItem,
    PromoCode,
    Region,
    District,
    DeliveryPrice,
    RatingType,
    LoyaltyProgram, 
    PromoReward,
)
from .models.company_info import (
    Branch,
    AboutUs,
    PrivacyPolicy,
    Contact,
    UserAgreement,
    FAQ,
    Document,
    SupportContact,
    CompanyBenefit,
    CompanyComment,
    WebPageInfo, 
    StaticPage, 
    RequestForm,
    LandingPageBanner,
)
from .models.product import (
    ProductTemplate,
    Variant,
    Option,
    Product,
    ProductOption,
    Discount,
    SavedProduct,
    Category,
    Brand,
    Offer,
    StockQuant,
    Location,
    WareHouse,
    ProductVariants,
    ProductRating,
    Currency,
    Pricelist,
    OilBrand,
    FilterBrand,
    ProductTemplateImage,
    Partner
)
from .models.booking import (
    Booking,
    BookingRating,
    Appointment,
    AppointmentWorkingDay,
    Resource,
)
from .models.garage import (
    CarModel,
    Firm,
    Car,
    OilChangedHistory,
    SomeColor,
    CarColor,
    OilChangeRating,
)
from .models.notification import NotificationTemplate, Notification
from .models.card import (
    Card,
    CardImages,
    LoyaltyCard,
    Invoice,
    CheckForUser,
    BalanceStatus,
    Balance,
    Cashback,
    BalanceUsageLimit,
)
from .models.edu_video import EduVideo
from django.utils.translation import gettext_lazy as _


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("id", "name_en", "name_ru", "name_uz", "created_at", "updated_at")
@admin.register(CheckForUser)
class checkAdmin(admin.ModelAdmin):
    list_display = ("id","transaction_number")
@admin.register(RatingType)
class RatingTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "odoo_id", "status", "name_en")


@admin.register(ProductTemplateImage)
class ProductTemplateImageAdmin(admin.ModelAdmin):
    list_display = ("id", "odoo_id", "product_template", "image")
    search_fields = ("product_template__name", "odoo_id")
    list_filter = ("product_template",)


@admin.register(OilChangeRating)
class OilChangeRatingAdmin(admin.ModelAdmin):
    list_display = ("id", "odoo_id", "description", "rating", "reviewer")
    search_fields = ("odoo_id", )


@admin.register(DeliveryPrice)
class DeliveryPriceAdmin(admin.ModelAdmin):
    list_display = ("id", "district", "price", "created_at", "updated_at")
    search_fields = ("district__name", "odoo_id")
    list_filter = ("district",)
    ordering = ("-created_at",)
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ProductRating)
class ProductRatingAdmin(admin.ModelAdmin):
    list_display = ("id", "odoo_id", "reviewer", "product", "rating", "created_at")


@admin.register(ProductVariants)
class ProductVariantsAdmin(admin.ModelAdmin):
    list_display = ("id", "odoo_id")


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at", "updated_at")
    search_fields = ("name",)


@admin.register(CompanyBenefit)
class CompanyBenefittAdmin(admin.ModelAdmin):
    list_display = ("id", "title_en", "description_en", "created_at")
    search_fields = (
        "title_en",
        "description_en",
    )


@admin.register(CompanyComment)
class CompanyCommentAdmin(admin.ModelAdmin):
    list_display = ("id", "company_name", "full_name_en", "position_en")
    search_fields = (
        "company_name",
        "full_name_en",
    )

@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    list_display = ("id", "title_en", "content_en", "include_form")
    search_fields = ("title_en", "title_uz", "title_ru")


@admin.register(RequestForm)
class ModelNameAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'organization', 'phone', 'email', 'source_page']
    search_fields = ['name', 'organization', 'phone', 'email', 'source_page__title_en']


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "region", "created_at", "updated_at")
    search_fields = (
        "name",
        "region__name",
    )
    list_filter = ("region",)


@admin.register(ProductTemplate)
class ProductTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "odoo_id", "name", "category")
    search_fields = (
        "name",
        "category__name_en",
        "category__name_uz",
        "category__name_ru",
    )
    list_filter = (
        "category__name_en",
        "category__name_uz",
        "category__name_ru",
    )


@admin.register(LoyaltyProgram)
class LoyaltyProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "branch", "currency", "active", "date_from", "date_to", "limit_usage", "max_usage")
    list_filter = ("active", "branch", "currency")
    search_fields = ("name", "odoo_id")
    ordering = ("-date_from",)


@admin.register(PromoReward)
class PromoRewardAdmin(admin.ModelAdmin):
    list_display = (
        "reward_type", "discount", "discount_applicability",
        "program", "discount_line_product", "discount_max_amount", "active"
    )
    list_filter = ("reward_type", "discount_applicability", "active")
    search_fields = ("description", "odoo_id")
    filter_horizontal = ("discount_product_ids",)
    autocomplete_fields = ("program", "discount_line_product")
    ordering = ("-id",)


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "program", "partner", "expiration_date", "active")
    list_filter = ("active", "program")
    search_fields = ("code", "odoo_id")
    autocomplete_fields = ("program", "partner")
    readonly_fields = ("odoo_id",)
    ordering = ("-id",)


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ("id", "odoo_id", "name")
    # filter_horizontal = ('name',)



@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ("id", "odoo_id", "variant", "name")
    search_fields = ("name", "variant__name")
    list_filter = ("variant",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "odoo_id", "product_template", "attribute_values", "is_top")
    search_fields = ("product_template__name", "odoo_id", )
    ordering = ("-created_at",)

    def attribute_values(self, obj):
        return ", ".join([attr.variant.name + " - " + attr.name for attr in obj.attributes.all()])


@admin.register(ProductOption)
class ProductOptionAdmin(admin.ModelAdmin):
    list_display = ("id", "option")
    search_fields = ("option__name",)
    list_filter = ("option",)


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "odoo_id", 
        "product",
        "user",
        "amount",
        "percent",
        "time_from",
        "time_to",
        "quantity",
    )
    search_fields = ("product__product_template__name",)
    list_filter = ("time_from", "time_to")


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("id", "odoo_id", "name", "category", "created_at")
    search_fields = ("category",)
    list_filter = ("created_at", "updated_at")


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("name", "odoo_id")
    search_fields = ("name", "odoo_id")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("id", "odoo_id", "branch")
    search_fields = ("branch__name",)


@admin.register(AppointmentWorkingDay)
class AppointmentWorkingDayAdmin(admin.ModelAdmin):
    list_display = ("id", "odoo_id", "opening_time", "closing_time", "day")
    search_fields = ("day", "appointment__name")


@admin.register(AboutUs)
class AboutUsAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "created_at", "updated_at")
    search_fields = ("title",)
    list_filter = ("created_at", "updated_at")


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("id", "phone1", "email1", "address")
    search_fields = ("phone1", "email1", "address")
    list_filter = ("email1",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "odoo_id",
        "user",
        "type",
        "status",
        "payment_status",
        "price",
        "created_at",
        "cancelled_at",
        "cancelled_at",
    )
    search_fields = ("odoo_id", "status", "payment_status", "type")
    list_filter = ("status", "payment_status", "type")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "odoo_id",
        "order",
        "product",
        "quantity",
        "price",
        "total_price",
    )
    search_fields = ("product__product_template__name",)
    list_filter = ("order",)


@admin.register(OrderRating)
class OrderRatingAdmin(admin.ModelAdmin):
    list_display = ("id", "odoo_id", "reviewer", "order", "rating", "created_at")
    search_fields = ("reviewer__first_name", "reviewer__last_name", "order__id")
    list_filter = ("rating",)


@admin.register(Basket)
class BasketAdmin(admin.ModelAdmin):
    list_display = ("id", "odoo_id", "user", "price", "created_at")
    search_fields = ("user__first_name", "user__last_name")
    list_filter = ("created_at",)
    readonly_fields = ["created_at"]


@admin.register(BasketItem)
class BasketItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "odoo_id",
        "basket",
        "product",
        "quantity",
        "price",
        "total_price",
    )
    search_fields = ("product__product_template__name",)
    list_filter = ("basket",)
    readonly_fields = ["price", "total_price"]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "odoo_id",
        "user",
        "car",
        "start_time",
        "end_time",
        "branch",
        "status",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "branch", "created_at", "updated_at")
    search_fields = ("user__info__first_name", "car__number", "branch__category")
    ordering = ("-created_at",)
    list_editable = ("status",)


@admin.register(BookingRating)
class BookingRatingAdmin(admin.ModelAdmin):
    list_display = ("id", "odoo_id", "reviewer", "booking", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("reviewer__username", "booking__id")
    ordering = ("-created_at",)


@admin.register(CarModel)
class CarModelAdmin(admin.ModelAdmin):
    list_display = ("id", "odoo_id", "name", "created_at", "updated_at")
    search_fields = ("name",)
    ordering = ("-created_at",)


@admin.register(Firm)
class FirmAdmin(admin.ModelAdmin):
    list_display = ("id", "odoo_id", "name", "created_at", "updated_at")
    search_fields = ("name",)
    ordering = ("-created_at",)


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "odoo_id",
        "user",
        "number",
        "firm",
        "model",
        "color",
        "created_at",
        "updated_at",
    )
    list_filter = ("firm", "model", "color", "created_at")
    search_fields = ("number", "firm__name", "model__name", "user__phone")
    ordering = ("-created_at",)


@admin.register(CarColor)
class CarColorAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "odoo_id",
        "some_color",
        "car_model",
        "image",
        "created_at",
        "updated_at",
    )
    list_filter = ("some_color", "car_model", "created_at")
    search_fields = ("car_model__name", "some_color__name_en")
    ordering = ("-created_at",)


@admin.register(SomeColor)
class SomeColorAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "odoo_id",
        "name_uz",
        "name_en",
        "name_ru",
        "color_code",
        "created_at",
        "updated_at",
    )
    search_fields = ("name_en",)
    ordering = ("-created_at",)


@admin.register(OilChangedHistory)
class OilChangedHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "odoo_id",
        "car",
        "last_oil_change",
        "distance",
        "oil_brand",
        "recommended_distance",
        "daily_distance",
        "created_at",
        "updated_at",
    )
    list_filter = ("car", "last_oil_change", "oil_brand", "created_at")
    search_fields = ("car__number", "oil_brand")
    ordering = ("-created_at",)


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "odoo_id", "title", "creator", "created_at", "updated_at")
    search_fields = ("title", "creator__username", "description", "condition")
    list_filter = ("creator", "created_at")
    ordering = ("-created_at",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "odoo_id",
        "title_uz",
        "title_en",
        "title_ru",
        "creator",
        "message_uz",
        "message_en",
        "message_ru",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "title_uz",
        "title_ru",
        "title_en",
        "creator__username",
        "message_uz",
        "message_en",
        "message_ru",
    )
    list_filter = ("creator", "created_at")
    ordering = ("-created_at",)


@admin.register(UserAgreement)
class UserAgreementAdmin(admin.ModelAdmin):
    list_display = ("title_en", "title_uz", "title_ru", "created_at", "updated_at")
    search_fields = ("title_en", "title_uz", "title_ru")
    list_filter = ("created_at", "updated_at")
    ordering = ("-created_at",)
    fieldsets = (
        (
            _("English Content"),
            {
                "fields": ("title_en", "description_en"),
            },
        ),
        (
            _("Uzbek Content"),
            {
                "fields": ("title_uz", "description_uz"),
            },
        ),
        (
            _("Russian Content"),
            {
                "fields": ("title_ru", "description_ru"),
            },
        ),
    )


@admin.register(PrivacyPolicy)
class PrivacyPolicyAdmin(admin.ModelAdmin):
    list_display = ("title_en", "title_uz", "title_ru", "created_at", "updated_at")
    search_fields = ("title_en", "title_uz", "title_ru")
    list_filter = ("created_at", "updated_at")
    ordering = ("-created_at",)
    fieldsets = (
        (
            _("English Content"),
            {
                "fields": ("title_en", "description_en"),
            },
        ),
        (
            _("Uzbek Content"),
            {
                "fields": ("title_uz", "description_uz"),
            },
        ),
        (
            _("Russian Content"),
            {
                "fields": ("title_ru", "description_ru"),
            },
        ),
    )


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = (
        "question_en",
        "question_uz",
        "question_ru",
        "order_number",
        "created_at",
    )
    search_fields = (
        "question_en",
        "question_uz",
        "question_ru",
        "answer_en",
        "answer_uz",
        "answer_ru",
    )
    list_filter = ("created_at", "updated_at")
    ordering = ("order_number",)
    fieldsets = (
        (
            _("English Content"),
            {
                "fields": ("question_en", "answer_en"),
            },
        ),
        (
            _("Uzbek Content"),
            {
                "fields": ("question_uz", "answer_uz"),
            },
        ),
        (
            _("Russian Content"),
            {
                "fields": ("question_ru", "answer_ru"),
            },
        ),
        (
            _("Settings"),
            {
                "fields": ("order_number",),
            },
        ),
    )


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "admin",
        "file_name_uz",
        "file_name_en",
        "file_name_ru",
        "file",
        "created_at",
    )
    search_fields = (
        "file_name_uz",
        "file_name_en",
        "file_name_ru",
    )
    list_filter = ("admin",)
    ordering = ("created_at",)


@admin.register(SavedProduct)
class SavedProductAdmin(admin.ModelAdmin):
    list_display = ["id", "odoo_id", "user", "product_template", "saved_at"]
    search_fields = ("user__info__first_name", )
    list_filter = (
        "user",
        "product_template",
    )
    ordering = ("saved_at",)


@admin.register(SupportContact)
class SupportContactAdmin(admin.ModelAdmin):
    list_display = ("id", "phone", "email")
    search_fields = ("phone",)
    list_filter = ("phone",)


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ["id", "image_en", "video_en", "caption_en", "expires_at"]
    ordering = ["created_at"]
    list_filter = ["created_at", "expires_at"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "odoo_id",
        "name_uz",
        "name_en",
        "name_ru",
        "created_at",
        "updated_at",
    ]
    search_fields = ("name_uz", "name_en", "name_ru")
    ordering = ["updated_at"]


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name_uz",
        "name_en",
        "name_ru",
        "image",
        "is_top",
        "created_at",
        "updated_at",
    ]
    search_fields = ("name_uz", "name_en", "name_ru")
    ordering = ["updated_at", "created_at"]


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = (
        "title_uz",
        "title_en",
        "title_ru",
        "start_date",
        "end_date",
        "created_at",
        "updated_at",
    )

    list_filter = ("start_date", "end_date", "created_at")

    search_fields = ("title_uz", "title_en", "title_ru", "odoo_id")

    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("title_uz", "title_en", "title_ru", "odoo_id", "image")}),
        ("Date range", {"fields": ("start_date", "end_date")}),
        (
            "Description",
            {"fields": ("description_uz", "description_en", "description_ru")},
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    date_hierarchy = "start_date"


@admin.register(CardImages)
class CardImagesAdmin(admin.ModelAdmin):
    list_display = ["id", "image"]
    search_fields = ["image"]


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "card_name", "card_number", "is_main", "is_active"]
    list_filter = ["is_main", "is_active"]
    search_fields = ["card_name", "card_number", "owner"]
    raw_id_fields = ["user", "background_image"]


@admin.register(LoyaltyCard)
class LoyaltyCardAdmin(admin.ModelAdmin):
    list_display = ["id", "card_name", "card_number", "balance", "is_active"]
    search_fields = ["card_name", "card_number"]
    list_filter = ["is_active"]
    raw_id_fields = ["car", "background_image"]


@admin.register(BalanceStatus)
class BalanceStatusAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "odoo_id",
        "name",
        "percentage",
        "minimum_amount",
        "next_minimum_amount",
        "created_at",
    ]
    list_filter = ["time_line"]
    search_fields = ["name", "description_en", "description_en", "description_ru"]


@admin.register(Balance)
class BalanceAdmin(admin.ModelAdmin):
    list_display = ["id", "odoo_id", "user", "balance", "balance_status", "created_at"]
    list_filter = ["balance_status", "created_at"]
    search_fields = ["user__info__first_name", "user__info__last_name"]
    raw_id_fields = ["user", "balance_status"]


@admin.register(Cashback)
class CashbackAdmin(admin.ModelAdmin):
    list_display = ["id", "odoo_id", "balance", "amount", "created_at"]
    list_filter = ["state", "created_at"]
    search_fields = [
        "balance__user__info__first_name",
        "balance__user__info__last_name",
    ]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "transaction_number",
        "status",
        "amount",
        "amount_payed",
        "created_time",
        "exp_time",
    ]
    list_filter = ["status"]
    search_fields = ["transaction_id"]
    raw_id_fields = ["user", "order", "booking"]


@admin.register(WareHouse)
class WareHouseAdmin(admin.ModelAdmin):
    list_display = ("name", "odoo_id", "code", "branch", "active", "last_sync")
    list_filter = ("active", "branch")
    search_fields = ("name", "code", "odoo_id")
    readonly_fields = ("last_sync",)
    fieldsets = (
        (
            None,
            {"fields": ("odoo_id", "name", "code", "branch", "active", "send_odoo")},
        ),
        ("Timestamps", {"fields": ("last_sync",), "classes": ("collapse",)}),
    )


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "odoo_id",
        "name",
        "send_odoo",
        "complete_name",
        "location_type",
        "warehouse",
        "active",
        "last_sync",
    )
    list_filter = ("active", "location_type", "warehouse")
    search_fields = ("name", "complete_name", "odoo_id")
    readonly_fields = ("last_sync",)
    fieldsets = (
        (None, {"fields": ("odoo_id", "name", "complete_name", "location_type")}),
        (
            "Relations",
            {
                "fields": ("warehouse", "parent_location", "branch"),
                "classes": ("collapse",),
            },
        ),
        ("Status", {"fields": ("active",), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("last_sync",), "classes": ("collapse",)}),
    )


@admin.register(StockQuant)
class StockQuantAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "odoo_id",
        "location",
        "quantity",
        "reserved_quantity",
        "last_sync",
    )
    list_filter = ("location", "location__warehouse")
    search_fields = ("product__product_template__name", "location__name", "odoo_id")
    readonly_fields = ("last_sync",)
    fieldsets = (
        (None, {"fields": ("odoo_id", "product", "location", "branch")}),
        ("Quantities", {"fields": ("quantity", "reserved_quantity")}),
        ("Timestamps", {"fields": ("last_sync",), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related("product", "location", "location__warehouse")


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "symbol", "active", "rounding")
    list_filter = ("active",)
    search_fields = ("name", "code")
    ordering = ("code",)


@admin.register(Pricelist)
class PricelistAdmin(admin.ModelAdmin):
    list_display = ("name", "branch", "currency", "active")
    list_filter = ("active", "branch", "currency")
    search_fields = ("name", "branch__name")
    raw_id_fields = ("branch",)


@admin.register(OilBrand)
class OilBrandAdmin(admin.ModelAdmin):
    list_display = ("id", "odoo_id", "name", "created_at", "updated_at")
    search_fields = ("name",)


@admin.register(FilterBrand)
class FilterBrandAdmin(admin.ModelAdmin):
    list_display = ("id", "odoo_id", "send_odoo", "name")
    search_fields = ("name", "odoo_id")


@admin.register(WebPageInfo)
class WebPageInfoAdmin(admin.ModelAdmin):
    list_display = ("id", "title_en", "title_uz", "title_ru")
    search_fields = ("title_en", "title_uz", "title_ru")


@admin.register(BalanceUsageLimit)
class BalanceUsageLimitAdmin(admin.ModelAdmin):
    list_display = ("id", "min_amount", "max_amount")
    search_fields = ("min_amount", "max_amount")


@admin.register(LandingPageBanner)
class LandingPageBannerAdmin(admin.ModelAdmin):
    list_display = ("id", "link")
    ordering = ("order_number",)


from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.apps import apps


@admin.register(OdooConnectorLog)
class OdooConnectorLogAdmin(admin.ModelAdmin):
    list_display = (
        "timestamp",
        "operation_type",
        "model_name",
        "instance_link",
        "status",
        "duration_display",
    )
    list_filter = ("operation_type", "status", "model_name")
    search_fields = ("model_name", "odoo_id", "error_message", "instance_id")
    readonly_fields = (
        "timestamp",
        "operation_type",
        "model_name",
        "local_model",
        "instance_id",
        "odoo_id",
        "status",
        "duration",
        "request_size",
        "response_size",
        "correlation_id",
        "batch_id",
        "request_data_prettified",
        "response_data_prettified",
        "error_message",
        "stack_trace",
    )

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "timestamp",
                    "operation_type",
                    "model_name",
                    "local_model",
                    "instance_id",
                    "odoo_id",
                    "status",
                    "duration_display",
                )
            },
        ),
        (
            "Request/Response",
            {
                "fields": (
                    "request_size",
                    "response_size",
                    "request_data_prettified",
                    "response_data_prettified",
                )
            },
        ),
        (
            "Error Details",
            {"fields": ("error_message", "stack_trace"), "classes": ("collapse",)},
        ),
        (
            "Context",
            {
                "fields": ("correlation_id", "batch_id", "retry_count", "last_retry"),
                "classes": ("collapse",),
            },
        ),
    )

    def instance_link(self, obj):
        if "." in obj.local_model:
            app_label, model_name = obj.local_model.split(".")
        else:
            app_label = "app"
            model_name = obj.local_model

        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            return f"Model {obj.local_model} not found"

        instance = model.objects.filter(pk=obj.instance_id).first()
        if not instance:
            return "-"

        url = reverse(
            f"admin:{model._meta.app_label}_{model._meta.model_name}_change",
            args=[instance.pk],
        )
        return format_html('<a href="{}">{}</a>', url, instance)

    instance_link.short_description = "Instance"

    def duration_display(self, obj):
        if obj.duration:
            return f"{obj.duration:.2f}s"
        return "-"

    duration_display.short_description = "Duration"

    def request_data_prettified(self, obj):
        if obj.request_data:
            return format_html("<pre>{}</pre>", json.dumps(obj.request_data, indent=2))
        return "-"

    request_data_prettified.short_description = "Request Data"

    def response_data_prettified(self, obj):
        if obj.response_data:
            return format_html("<pre>{}</pre>", json.dumps(obj.response_data, indent=2))
        return "-"

    response_data_prettified.short_description = "Response Data"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(EduVideo)
class EduVideoAdmin(admin.ModelAdmin):
    list_display = ("title", "description", "video_type", "video_url")
    search_fields = ("title", "description")
    list_filter = ("video_type",)