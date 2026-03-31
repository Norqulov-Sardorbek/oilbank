from celery import shared_task
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.views import APIView
from rest_framework import filters
from rest_framework.response import Response
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiExample,
    OpenApiTypes,
    OpenApiParameter,
)
from rest_framework.permissions import IsAuthenticated, AllowAny, SAFE_METHODS
from rest_framework.viewsets import ModelViewSet, ViewSet
from django.core.cache import cache
from drf_yasg import openapi
import logging, subprocess, os, uuid

logger = logging.getLogger(__name__)
import threading
import time
from decimal import Decimal, ROUND_DOWN
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q

from utils.pagination.paginations import DefaultLimitOffSetPagination
from app.models.product import Discount, Pricelist
from app.serializers.order import *
from django.utils import timezone
from app.permissions import IsAdminOrReadOnly, IsAdminUserCustom
from app.custom_filters import OrderFilter
from app.models.card import Invoice
import os, requests, json
from drf_yasg.utils import swagger_auto_schema
from user.models import MulticardConfig
from app.models.card import Card, Balance, BalanceUsageLimit
from django.http import HttpResponse
from django.template.loader import get_template
from django.core.files.storage import default_storage
from django.utils.translation import activate, get_language


def get_basket(user):
    basket, _ = Basket.objects.get_or_create(user=user, defaults={"price": 0})
    return basket


def _calculate_delivery_promocode_discount(order, delivery_price, promocode_discount):
    total_item_price = order.total_price

    if total_item_price <= 0 or delivery_price <= 0:
        return Decimal("0.00")

    proportion = delivery_price / total_item_price
    discount_amount = (promocode_discount * proportion).quantize(Decimal("0.01"))
    return max(Decimal("0.00"), discount_amount)


def get_token_and_store_id():
    url = "https://mesh.multicard.uz/auth"
    headers = {
        "Content-Type": "application/json",
    }
    # payload = {"application_id": "rhmt_test", "secret": "Pw18axeBFo8V7NamKHXX"}
    config = MulticardConfig.get_instance()
    if not config:
        return {"success": False, "message": "Config is not set"}
    payload_real = {
        "application_id": config.application_id,
        "secret": config.secret_key,
    }  # prod

    response = requests.post(url, headers=headers, data=json.dumps(payload_real))

    if response.status_code == 200:
        data = response.json()
        token_str = data.get("token")
        return {"success": True, "token": token_str, "store_id": config.store_id}
    else:
        raise ValueError(
            f"Error fetching token: {response.status_code}, {response.text}"
        )


class RegionViewSet(ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]


class DistrictViewSet(ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    queryset = District.objects.select_related("region").all()
    serializer_class = DistrictSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["region"]
    search_fields = ["name__name"]


@extend_schema_view(
    list=extend_schema(
        summary="List of user's orders",
        description="Retrieve all orders created by the authenticated user. This includes completed, pending, and cancelled orders.",
        tags=["Orders"],
        responses={200: OrderDetailSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Get specific order",
        description="Retrieve detailed information for a single order including items, delivery info, region, district, etc.",
        tags=["Orders"],
        responses={200: OrderDetailSerializer},
    ),
    create=extend_schema(
        summary="Create a new order",
        description=(
            "Create a new order based on the current basket.\n"
            "- For delivery: requires `address_id`.\n"
            "- For pickup: requires `branch` and `pickup_time`.\n"
            "- Optionally include a `promocode`.\n"
            "- Handles payment logic if payment method is `CLICK`, `PAYME`, `UZUM`, `CARD` or ''ON_RECEIVE.\n"
            "- Basket must not be empty."
            "- "
        ),
        tags=["Orders"],
        request=OrderCreateSerializer,
        responses={
            201: OrderDetailSerializer,
            400: OpenApiExample(
                "Empty basket error", value={"detail": "Your basket is empty"}
            ),
        },
    ),
    partial_update=extend_schema(
        summary="Partially update an order",
        description="Update quantity of product in an existing order.",
        tags=["Orders"],
        request=OrderUpdateSerializer,
        responses={200: OrderDetailSerializer},
    ),
    destroy=extend_schema(
        summary="Delete an order",
        description="Delete a specific order by ID. Only works if order is not yet completed.",
        tags=["Orders"],
    ),
)
class OrderViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    filterset_class = OrderFilter
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    ordering = ["-id"]
    ordering_fields = ["id", "created_at", "updated_at"]
    queryset = Order.objects.select_related(
        "user", "branch", "region", "district", "promocode"
    ).prefetch_related("items")

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        elif self.action == "validate_promo":
            return PromoCodeValidationSerializer
        elif self.action in ["update", "partial_update"]:
            return OrderUpdateSerializer
        return OrderDetailSerializer

    def get_queryset(self):
        # return self.queryset.all()
        return self.queryset.filter(user=self.request.user)

    @extend_schema(
        summary="Validate promo code",
        description="Validate a promo code against the current user's basket.",
        tags=["Orders"],
        request=PromoCodeValidationSerializer,
        responses={
            200: OpenApiExample(
                "Valid promo response",
                value={
                    "valid": True,
                    "discount_amount": 5000,
                    "current_total": 60000,
                    "new_total": 55000,
                },
            ),
            400: OpenApiExample(
                "Invalid or expired promo",
                value={"valid": False, "detail": "Invalid or expired promo code"},
            ),
        },
    )
    @action(detail=False, methods=["post"], url_path="validate-promo")
    def validate_promo(self, request):
        """Promo code validation endpoint"""
        basket = get_basket(request.user)
        if not basket.items.exists():
            return Response(
                {"detail": _("Your basket is empty")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"valid": False, "detail": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        promocode = serializer.validated_data["code"]
        response = self._validate_promocode(promocode, basket)

        if not response["valid"]:
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        return Response(response)

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            basket = get_basket(request.user)
            if not basket.items.exists():
                return Response(
                    {"detail": _("Your basket is empty")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            from django.conf import settings

            MAX_ORDER_AMOUNT = Decimal(str(settings.MAX_ORDER_AMOUNT))
            if basket.price > MAX_ORDER_AMOUNT:
                return Response(
                    {
                        "detail": _(
                            "Order amount exceeds the maximum limit of {}"
                        ).format(MAX_ORDER_AMOUNT),
                        "max_amount": str(MAX_ORDER_AMOUNT),
                        "current_amount": str(basket.price),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            accept_language = request.headers.get("Accept-Language", "en")

            # Promocode validation
            promocode = data.get("promocode")
            address = data.pop("address_id", None)
            discount_amount = Decimal("0.0")
            card_id = data.pop("card_id", None)
            use_balance = data.pop("use_balance", False)
            balance_amount_used = Decimal(str(data.pop("balance_amount", "0.0")))
            secondary_payment_method = data.pop("secondary_payment_method", None)
            user = User.objects.filter(pk=request.user.pk).first()
            payment_method = data.get("payment_method", None)
            delivery_price = Decimal("0.00")

            if address and address.district:
                try:
                    delivery_price = address.district.delivery_prices_destrict.price
                except DeliveryPrice.DoesNotExist:
                    delivery_price = Decimal("0.0")

            if promocode:
                validation = self._validate_promocode(promocode, basket, delivery_price, balance_amount_used)
                if not validation["valid"]:
                    return Response(
                        {"detail": validation["detail"]},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                discount_amount = validation["discount_amount"]

            # Balance validation
            balance = Balance.objects.filter(user=user).first()
            remaining_amount = basket.price - discount_amount + delivery_price

            if use_balance and balance_amount_used > 0:
                if not balance:
                    return Response(
                        {"detail": _("No balance available for this user")},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                balance_limit = BalanceUsageLimit.objects.first()
                if balance_limit:
                    if balance_amount_used < balance_limit.min_amount:
                        return Response(
                            {
                                "message": _(
                                    "Cashback usage is not more than {min_amount}."
                                ).format(min_amount=str(balance_limit.min_amount))
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    if balance_amount_used > balance_limit.max_amount:
                        return Response(
                            {
                                "message": _(
                                    "Cashback usage is more than {max_amount} to use cashback."
                                ).format(max_amount=str(balance_limit.max_amount))
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                # Validate provided balance amount
                if balance_amount_used > balance.balance:
                    return Response(
                        {
                            "message": _(
                                "Requested balance amount exceeds available balance"
                            ),
                            "requested_amount": str(balance_amount_used),
                            "current_balance": str(balance.balance),
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                
                if remaining_amount > balance_amount_used and payment_method == "CASHBACK":
                    return Response(
                        {
                            "message": _(
                                "Requested balance amount is not enough to pay the order"
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                
                if remaining_amount - balance_amount_used < 500 and payment_method == "MIXED":
                    return Response(
                        {
                            "message":_(
                                "The non-cashback payment must cover at least 500 units for mixed payments"
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if balance_amount_used > remaining_amount:
                    return Response(
                        {
                            "message": _(
                                "Requested balance amount exceeds the order amount after discounts"
                            ),
                            "requested_amount": str(balance_amount_used),
                            "remaining_amount": str(remaining_amount),
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Apply discounts to items
            for item in basket.items.all():
                discount = _get_applicable_discount(user, item.product, timezone.now()
                )
                if discount is not None:
                    break

            pricelist = (
                Pricelist.objects.filter(items=discount).first() if discount else None
            )

            # Create order
            order = self._create_order(
                user=user,
                basket=basket,
                address_id=address,
                region=address.region if address else None,
                district=address.district if address else None,
                promocode=promocode,
                pricelist=pricelist,
                discount_amount=discount_amount,
                balance_amount=balance_amount_used,
                **{
                    k: v
                    for k, v in data.items()
                    if k not in ["promocode", "use_balance", "balance_amount", "secondary_payment_method"]
                },
            )

            if use_balance and balance and balance_amount_used > 0:
                # cashback_product = Product.objects.filter(name="Cashback").first()
                cashback_product = Product.objects.filter(
                    product_type="CASHBACK"
                ).first()
                if cashback_product:
                    OrderItem.objects.create(
                        order=order,
                        product=cashback_product,
                        quantity=1,
                        price=-balance_amount_used,
                        total_price=-balance_amount_used,
                        discount_amount=0.0,
                    )

            # Handle payment
            if data.get("payment_method") in [
                "PAYME",
                "XAZNA",
                "ALIF",
                "BEEPUL",
                "ANORBANK",
                "OSON",
                "UZUM",
                "CLICK",
                "CARD",
            ]:
                multicard_url = self._handle_multicard_payment(
                    order,
                    data.get("payment_method"),
                    accept_language,
                    request.data,
                    balance_amount_used,
                    discount_amount,
                )
                if not multicard_url["success"]:
                    return Response(
                        {"type": order.payment_method, "detail": multicard_url},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                basket.items.all().delete()
                basket.delete()
                return Response(
                    {"type": order.payment_method, "detail": multicard_url["message"]},
                    status=status.HTTP_200_OK,
                )
            elif data.get("payment_method") == "MIXED" and secondary_payment_method in [
                "PAYME",
                "XAZNA",
                "ALIF",
                "BEEPUL",
                "ANORBANK",
                "OSON",
                "UZUM",
                "CLICK",
                "CARD",
            ]:
                multicard_url = self._handle_mixed_payment(
                    order,
                    secondary_payment_method,
                    accept_language,
                    request.data,
                    balance_amount_used,
                    discount_amount,
                )
                if not multicard_url["success"]:
                    return Response(
                        {"type": order.payment_method, "detail": multicard_url},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                basket.items.all().delete()
                basket.delete()
                return Response(
                    {"type": order.payment_method, "detail": multicard_url["message"]},
                    status=status.HTTP_200_OK,
                )

            basket.items.all().delete()
            basket.delete()

            return Response(
                {
                    "type": order.payment_method,
                    "message": _("Order created successfully"),
                    "detail": OrderDetailSerializer(
                        order, context={"request": request}
                    ).data,
                },
                status=status.HTTP_201_CREATED,
            )

    def _calculate_item_promocode_discount(self, order, order_item, promocode_discount):
        if order.price <= 0 or order_item.total_price <= 0:
            return Decimal("0.00")

        proportion = order_item.total_price / order.total_price
        discount_amount = (promocode_discount * proportion).quantize(Decimal("0.01"))
        return max(Decimal("0.00"), discount_amount)

    @extend_schema(
        summary="Pay for order with multicard",
        description="Handles external multicard payment system integration for an order.",
        tags=["Orders"],
        request=OrderPaymentSerializer,
        responses={
            200: OpenApiExample(
                "Payment success",
                value={
                    "type": "CLICK",
                    "detail": "https://mesh.multicard.uz/checkout?uuid=abc123",
                },
            )
        },
    )
    def _handle_multicard_payment(
        self,
        order,
        payment_type,
        language,
        request_data,
        balance_amount_used=Decimal("0.0"),
        promocode_discount=Decimal("0.0"),
    ):
        try:
            token_and_store_id = get_token_and_store_id()
            if not token_and_store_id["success"]:
                return {"success": False, "message": "Config is not set"}

            d_token = token_and_store_id["token"]
            store_id = token_and_store_id["store_id"]

            BASE_URL = os.getenv("BASE_URL", "https://api.car-land.uz")
            url = "https://mesh.multicard.uz/payment"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {d_token}",
            }
            
            amount = order.price
            if amount < 500:
                return {
                    "success": False,
                    "message": _(
                        "Amount is less than 500 UZS after cashback deduction"
                    ),
                }

            products_data = []
            
            # Calculate total order value for balance amount distribution (excluding delivery, cashback, coupon items)
            eligible_items = [
                item for item in order.items.all()
                if item.product and item.product.product_type not in ['CASHBACK', 'DELIVERY_PRICE', 'COUPON']
            ]
            
            total_eligible_value = sum(item.total_price for item in eligible_items)
            
            for item in order.items.all():
                # Skip items that shouldn't be sent to Multicard
                if item.product and item.product.product_type not in ['CASHBACK', 'DELIVERY_PRICE', 'COUPON']:
                    mxik = item.product.mxik
                    package_code = item.product.package_code
                    
                    if not mxik:
                        mxik = item.product.product_template.category.mxik
                    if not package_code:
                        package_code = item.product.product_template.category.package_code

                    # Use your existing function for promocode distribution
                    item_promocode_discount = self._calculate_item_promocode_discount(
                        order, item, promocode_discount
                    )
                    
                    # Calculate proportional balance amount distribution
                    if total_eligible_value > 0:
                        item_proportion = item.total_price / total_eligible_value
                        item_balance_discount = balance_amount_used * item_proportion
                    else:
                        item_balance_discount = Decimal("0.0")
                    
                    # Get existing item discount
                    item_discount_amount = item.discount_amount if item.discount_amount else Decimal("0.0")
                    
                    # Calculate totals
                    item_price = float(item.total_price)
                    total_discounts = float(
                        item_discount_amount + item_promocode_discount + item_balance_discount
                    )
                    final_item_total = item_price - total_discounts
                    
                    # Ensure we don't have negative totals
                    if final_item_total < 0:
                        final_item_total = 0
                        total_discounts = item_price

                    products_data.append(
                        {
                            "qty": item.quantity,
                            "price": item_price * 100,  # Convert to tiyin
                            "mxik": mxik,
                            "package_code": package_code,
                            "name": item.product.name,
                            "discount": total_discounts * 100,  # Convert to tiyin
                            "other": 0.0,
                            "total": item_price * item.quantity * 100,  # Convert to tiyin
                        }
                    )

            # Add delivery price if exists
            if order.delivery_price > 0:
                delivery_discount  = _calculate_delivery_promocode_discount(order, order.delivery_price, promocode_discount)
                products_data.append(
                    {
                        "qty": 1,
                        "price": float(order.delivery_price * 100),
                        "mxik": "10112006002000000",
                        "package_code": "1209779",
                        "name": "Delivery Price",
                        "discount":float(delivery_discount * 100),
                        "other": 0.0,
                        "total": float(order.delivery_price * 100),
                    }
                )

            uuid_ref = uuid4()
            # Instead of save(), use update()
            Order.objects.filter(pk=order.pk).update(raxmat_reference=uuid_ref, send_odoo=False)
            
            data = {
                "store_id": store_id,
                "amount": float(amount * 100),
                "currency": "UZS",
                "lang": language,
                "invoice_id": str(uuid_ref),
                "callback_url": f"{BASE_URL}/api/multicard/invoice-response/",
                "ofd": products_data,
            }
            
            # Set payment system based on payment type
            payment_system_mapping = {
                "CLICK": "click",
                "UZUM": "uzum", 
                "PAYME": "payme",
                "XAZNA": "xazna",
                "ALIF": "alif",
                "BEEPUL": "beepul",
                "ANORBANK": "anorbank",
                "OSON": "oson"
            }
            
            if payment_type in payment_system_mapping:
                data["payment_system"] = payment_system_mapping[payment_type]

            print(f"Multicard sending URL: {url}\nData: {data}")
            response = requests.post(url, data=json.dumps(data), headers=headers)
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"Multicard response data: {response_data}")
                checkout_url = response_data.get("data", {}).get("checkout_url")
                uuid = response_data.get("data", {}).get("uuid")
                
                # Use update here as well
                Order.objects.filter(pk=order.pk).update(raxmat_payment_id=uuid)
                return {"success": True, "message": checkout_url}
            else:
                return {"success": False, "message": response.json()}
                
        except Exception as e:
            return {"success": False, "message": str(e)}

    @extend_schema(
        summary="Pay for order with mixed payment",
        description="Handles mixed payment (balance + multicard) for an order.",
        tags=["Orders"],
        request=OrderPaymentSerializer,
        responses={
            200: OpenApiExample(
                "Mixed payment success",
                value={
                    "type": "MIXED",
                    "detail": "https://mesh.multicard.uz/checkout?uuid=abc123",
                },
            )
        },
    )
    def _handle_mixed_payment(
        self,
        order,
        secondary_payment_method,
        language,
        request_data,
        balance_amount_used,
        promocode_discount=Decimal("0.0"),
    ):
        return self._handle_multicard_payment(
            order,
            secondary_payment_method,
            language,
            request_data,
            balance_amount_used,
            promocode_discount,
        )

    def _create_order(
        self,
        user,
        basket,
        address_id,
        region,
        district,
        promocode=None,
        discount_amount=0,
        balance_amount=0,
        **kwargs,
    ):
        """Helper method to create order with items"""
        raxmat_reference = None
        payment_status = "PENDING"

        if kwargs.get("payment_method") in [
            "PAYME", "XAZNA", "ALIF", "BEEPUL", "ANORBANK", "OSON", "UZUM", "CLICK", "CARD", "CASHBACK", "MIXED",
        ]:
            raxmat_reference = str(uuid4())
            if kwargs.get("payment_method") == "CASHBACK":
                payment_status = "COMPLETED"

        has_delivery_price = False
        delivery_price = Decimal("0.00")
        if district:
            try:
                delivery_price = district.delivery_prices_destrict.price
                has_delivery_price = True
            except DeliveryPrice.DoesNotExist:
                delivery_price = Decimal("0.0")

        balance = Balance.objects.filter(user=user).first()
        balance_status_name = (
            balance.balance_status.name if balance and balance.balance_status else None
        )
        persent = (
            round(balance.balance_status.percentage) if balance and balance.balance_status else 0
        )
        products_discount = Decimal("0.0")
        for item in basket.items.all():
            # if item.product and item.product.name not in ['Cashback', 'delivery_price']:
            if item.product and item.product.product_type not in ['CASHBACK', 'DELIVERY_PRICE', 'COUPON']:
                product_discount = (float(item.discount_amount)
                            if item.discount_amount
                            else 0.0
                        )
                product_discount = Decimal(str(product_discount)) if not isinstance(product_discount, Decimal) else product_discount
                products_discount += product_discount

        print("Total Product Discounts:", products_discount)
        
        discount_amount = Decimal(str(discount_amount)) if not isinstance(discount_amount, Decimal) else discount_amount
        balance_amount = Decimal(str(balance_amount)) if not isinstance(balance_amount, Decimal) else balance_amount
        products_discount = Decimal(str(products_discount)) if not isinstance(products_discount, Decimal) else products_discount
        
        subtotal = basket.price
        total_before_discounts = subtotal + delivery_price  
        final_price = subtotal - discount_amount - balance_amount - products_discount + delivery_price
        total_items_count = basket.items.count()  # Basket items
        if has_delivery_price:
            total_items_count += 1  # Delivery price item
        if promocode:
            total_items_count += 1  # Promo code discount item
        if balance_amount > 0:
            total_items_count += 1  # Cashback item (created earlier in the create method)
        
        order = Order.objects.create(
            user=user,
            price=final_price,
            status="PENDING",
            region=region,
            total_price=total_before_discounts,
            district=district,
            promocode_amount=discount_amount,
            discount_amount=products_discount,
            delivery_price=delivery_price,
            payment_status=payment_status,
            address_id=address_id,
            promocode=promocode,
            raxmat_reference=raxmat_reference,
            balance_amount=balance_amount,
            balance_status_name=balance_status_name,
            balance_percentage=persent,
            total_items_count=total_items_count,
            **kwargs,
        )

        for item in basket.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.price,
                total_price=item.total_price,
                discount_amount=item.discount_amount,
                discount_percent=item.discount_percent,
            )

        
        if has_delivery_price:
            # delivery_price_product = Product.objects.filter(name="delivery_price").first()
            delivery_price_product = Product.objects.filter(product_type="DELIVERY_PRICE").first()
            OrderItem.objects.create(
                order=order,
                product=delivery_price_product,
                quantity=1,
                price=delivery_price,
                total_price=delivery_price,
                discount_amount=0,
                discount_percent=0,
            )
        # if order.type == "DELIVERY" or order.payment_status == "COMPLETED":

        #     thread = threading.Thread(target=delayed_update_order, args=[order.pk])
        #     thread.daemon = True  
        #     thread.start()
        

        if promocode:
            promo_code_product = promocode.program.promocode_rewards.filter(active=True).first().discount_line_product
            if promo_code_product:
                OrderItem.objects.create(
                    order=order,
                    product=promo_code_product,
                    quantity=1,
                    price=-order.promocode_amount,
                    total_price=-order.promocode_amount,
                    discount_amount=0,
                    discount_percent=0,
                )

        return order

    def _validate_promocode(self, promocode, basket, delivery_price=Decimal("0.0"), balance_amount_used=Decimal("0.0")):
        serializer = PromoCodeValidationSerializer(data={"code": promocode.code}, context={"request": self.request})
        if not serializer.is_valid():
            return {"valid": False, "detail": serializer.errors}
        promocode = serializer.promo
        total_price = basket.price + delivery_price - balance_amount_used
        discount_amount = self._calculate_discount(promocode, basket, total_price)
        promo_reward = promocode.program.promocode_rewards.filter(active=True).first()

        return {
            "valid": True,
            "code": promocode.code,
            "discount_amount": discount_amount,
            "discount_percent": promo_reward.discount if promo_reward else Decimal("0.0"),
            "current_total": total_price,
            "new_total": total_price - discount_amount,
        }


    def _calculate_discount(self, promocode, basket, total_price=Decimal("0.0")):
        from decimal import Decimal, ROUND_HALF_UP
        total_discount = Decimal("0.0")
        promo_reward = promocode.program.promocode_rewards.filter(active=True).first()

        if not promo_reward:
            return total_discount

        discount_rate = Decimal(str(promo_reward.discount)) / Decimal("100")
        max_discount = Decimal(str(promo_reward.discount_max_amount))

        available_products = promo_reward.discount_product_ids.all()
        available_category = promo_reward.discount_product_category_id

        if promo_reward.discount_applicability == "specific":
            for item in basket.items.all():
                product_category = item.product.product_template.category if item.product and item.product.product_template else None
                if item.product in available_products or (
                        available_category and product_category == available_category):
                    total_discount += item.price * discount_rate

        elif promo_reward.discount_applicability == "order":
            total_discount = total_price * discount_rate

        elif promo_reward.discount_applicability == "cheapest":
            cheapest_item = basket.items.all().order_by("price").first()
            if cheapest_item:
                print(cheapest_item.quantity)
                total_discount = cheapest_item.price * discount_rate * cheapest_item.quantity

        total_discount = total_discount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return min(total_discount, max_discount) if max_discount != Decimal("0.0") else total_discount


class OrderMulticardResponceApiView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=PaymentDataSerializer)
    def post(self, request):
        try:
            # if serializer.is_valid():
            validated_data = request.data
            store_id = validated_data.get("store_id")
            amount = validated_data.get("amount")
            invoice_id = validated_data.get("invoice_id")
            invoice_uuid = validated_data.get("invoice_uuid")
            payment_time = validated_data.get("payment_time")
            billing_id = validated_data.get("billing_id")
            uuid = validated_data.get("uuid")
            sign = validated_data.get("sign")

            order = Order.objects.filter(raxmat_reference=invoice_id).first()

            if not order:
                return Response(
                    {"success": False, "message": "Order not found"},
                    status=status.HTTP_200_OK,
                )

            order.raxmat_payment_id = uuid
            order.payment_time = payment_time
            order.payment_status = "COMPLETED"
            order.save(update_fields=["raxmat_payment_id", "payment_time", "payment_status"])

            threading.Thread(target=get_check, args=(order,)).start()

            return Response(
                {
                    "success": True,
                    "message": "Payment successful",
                },
                status=status.HTTP_200_OK,
            )


        except Exception as e:
            return Response(
                {"success": False, "message": "Order not found"},
                status=status.HTTP_200_OK,
            )


class ReseaveMulticardCardPaymentOPT(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["uuid", "otp"],
            properties={
                "uuid": openapi.Schema(
                    type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID
                ),
                "otp": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="OTP that is send to user"
                ),
            },
        )
    )
    def put(self, request):
        try:
            uuid = request.data.get("uuid")
            otp = request.data.get("otp")

            # Validate input first
            if not uuid or not otp:
                return Response(
                    {"detail": "Both uuid and otp are required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            cache_key = f"payment_uuid_{uuid}"
            cached_data = cache.get(cache_key)

            if not cached_data:
                return Response(
                    {"detail": "Order not found or session expired"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if self.request.user.pk != cached_data["user_id"]:
                return Response(
                    {"detail": "Unauthorized access to this order"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Call Multicard API with timeout
            url = f"https://mesh.multicard.uz/payment/{uuid}"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {cached_data['token']}",
            }
            data = {"otp": otp}
            print(f"\n\n\n\n\n\nMulticard payment reseave data: {data}\n\n\n\n\n\n")

            try:
                response = requests.put(url=url, data=json.dumps(data), headers=headers)
                print(
                    f"\n\n\n\n\n\nMulticard payment reseave response: {response.json()}\n\n\n\n\n\n"
                )
            except requests.Timeout:
                return Response(
                    {"detail": "Payment service timeout"},
                    status=status.HTTP_504_GATEWAY_TIMEOUT,
                )
            except requests.RequestException as e:
                return Response(
                    {"detail": f"Payment service error: {str(e)}"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            response_data = response.json()
            if not response_data.get("success", False):
                return Response(
                    {"detail": response_data}, status=status.HTTP_400_BAD_REQUEST
                )

            # Get data and process in transaction
            try:
                with transaction.atomic():
                    order = Order.objects.get(id=cached_data["order_id"])
                    data = response_data.get("data")

                    invoice = Invoice.objects.create(
                        amount=order.price,
                        user=order.user,
                        order=order,
                        exp_time=timezone.now(),
                        status=Invoice.Status.PAID,
                        transaction_id=data.get("uuid"),
                        amount_payed=int(data.get("payment_amount")) / 100,
                    )
                    order.raxmat_payment_id = data.get("uuid")
                    order.payment_status = "COMPLETED"
                    order.save(update_fields=["payment_status", "raxmat_payment_id"])

                    threading.Thread(target=get_check, args=(order)).start()

                    return Response(
                        {"detail": "order paid successfully"}, status=status.HTTP_200_OK
                    )

            except Exception as e:
                logger.error(f"Transaction failed: {str(e)}")
                return Response(
                    {"error": "Failed to complete transaction"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return Response(
                {"error": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema_view(
    list=extend_schema(
        summary="Get the current user's basket",
        description="Returns the basket for the authenticated user with all the items and total price.",
        responses={200: BasketGetSerializer},
    ),
    update_item=extend_schema(
        summary="Update basket items",
        description="Add, update quantity, or remove items from the user's basket. Setting quantity to 0 removes the item.",
        request=BasketUpdateSerializer,
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Add item example",
                value={"product_id": 1, "quantity": 2},
                request_only=True,
            ),
            OpenApiExample(
                "Remove item example",
                value={"product_id": 1, "quantity": 0},
                request_only=True,
            ),
            OpenApiExample(
                "Success response", value={"detail": "Updated"}, response_only=True
            ),
        ],
    ),
    bulk_update=extend_schema(
        summary="Bulk update basket items",
        description="Update multiple items in the user's basket at once. Each item can be added, updated, or removed (if quantity = 0).",
        request=BasketBulkUpdateSerializer,
        responses={
            200: BasketGetSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Bulk update example",
                value={
                    "items": [
                        {"product_id": 1, "quantity": 2},
                        {"product_id": 2, "quantity": 0},
                    ]
                },
                request_only=True,
            ),
            OpenApiExample(
                "Success response",
                value={"basket": "updated basket data here"},
                response_only=True,
            ),
        ],
    ),
)
class BasketViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Basket.objects.select_related("user")
            .prefetch_related("items__product")
            .filter(user=self.request.user)
        ).exclude(items__product__product_type__in=["CASHBACK", "DELIVERY_PRICE", "COUPON"])

    def list(self, request):
        basket = get_basket(request.user)
        serializer = BasketGetSerializer(basket, context={"request": request})
        return Response(serializer.data)

    @action(detail=False, methods=["put"], url_path="update-item")
    def update_item(self, request):
        serializer = BasketUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data["product_id"]
        quantity = serializer.validated_data["quantity"]
        now = timezone.now()

        with transaction.atomic():
            basket = get_basket(request.user)
            product = (
                Product.objects.select_related(
                    "product_template__category", "product_template__branch"
                )
                .filter(id=product_id)
                .first()
            )
            if not product:
                return Response({"detail": "Product not found."}, status=404)

            discount = _get_applicable_discount(request.user, product, now)
            final_price, discount_amount, discount_percent = (
                self._calculate_discounted_price(product.price, discount)
            )

            if quantity == 0:
                basket.items.filter(product=product).delete()
            else:
                print(f"Product ID: {product_id}, Quantity: {quantity}, Final Price: {final_price}, Discount Amount: {discount_amount}, Discount Percent: {discount_percent}")
                total_price = final_price * quantity
                discount_amount = discount_amount * quantity
                print(f"Total Price: {total_price}, Discount Amount: {discount_amount}")

                BasketItem.objects.update_or_create(
                    basket=basket,
                    product=product,
                    defaults={
                        'quantity': quantity,
                        'price': final_price,
                        'total_price': total_price,
                        'discount_amount': discount_amount,
                        'discount_percent': discount_percent
                    }
                )

            basket.update_total()
            return Response(
                BasketGetSerializer(basket, context={"request": request}).data
            )

    @action(detail=False, methods=["put"], url_path="bulk-update")
    def bulk_update(self, request):
        serializer = BasketBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        items = serializer.validated_data["items"]
        now = timezone.now()
        basket = get_basket(request.user)

        with transaction.atomic():
            for item in items:
                product = (
                    Product.objects.select_related(
                        "product_template__category", "product_template__branch"
                    )
                    .filter(id=item["product_id"])
                    .first()
                )
                if not product:
                    continue

                discount = _get_applicable_discount(request.user, product, now)
                final_price, discount_amount, discount_percent = (
                    self._calculate_discounted_price(product.price, discount)
                )

                if item["quantity"] == 0:
                    basket.items.filter(product=product).delete()
                else:
                    BasketItem.objects.update_or_create(
                        basket=basket,
                        product=product,
                        defaults={
                            "quantity": item["quantity"],
                            "price": final_price,
                            "total_price": final_price * item["quantity"],
                            "discount_amount": discount_amount * item["quantity"],
                            "discount_percent": discount_percent,
                        },
                    )

            basket.update_total()
            return Response(
                BasketGetSerializer(basket, context={"request": request}).data
            )

    @extend_schema(
        methods=["DELETE"],
        operation_id="clearBasket",
        description="Clear all items from the authenticated user's basket.",
        summary="Clear Basket",
        responses={
            204: None,
            401: {"description": "Unauthorized"},
        },
        tags=["Basket"],
    )
    @action(detail=False, methods=["delete"], url_path="clear")
    def clear_basket(self, request):
        """
        Clears the basket of the currently authenticated user.
        Removes all items and resets the total price.
        """
        basket = get_basket(request.user)
        basket.items.all().delete()
        basket.update_total()
        return Response(
            {"detail": _("Basket has been cleared.")}, status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=False, methods=["delete"], url_path="bulk-delete")
    def bulk_delete(self, request):
        """
        Removes multiple products from the authenticated user's basket.
        Accepts a list of product IDs to be removed.
        """
        serializer = BasketBulkDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_ids = serializer.validated_data["product_ids"]
        basket = get_basket(request.user)

        basket.items.filter(product__id__in=product_ids).delete()
        basket.update_total()

        return Response(
            {"detail": _("Selected products have been removed from your basket.")},
            status=status.HTTP_204_NO_CONTENT
        )

    def _calculate_discounted_price(self, original_price, discount):
        if not discount:
            return Decimal(str(original_price)).quantize(Decimal("0.01")), Decimal('0.00'), 0.0

        discount_amount = Decimal("0.00")
        discount_percent = 0.0

        original_price = Decimal(str(original_price)).quantize(Decimal("0.01"))

        if discount.amount:
            discount_amount = Decimal(str(discount.amount)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            discount_percent = float((discount_amount / original_price) * 100) if original_price > 0 else 0.0
            final_price = max(Decimal('0.00'), original_price - discount_amount)
        elif discount.percent:
            discount_percent = Decimal(str(discount.percent))
            discount_amount = (original_price * (discount_percent / Decimal('100')))
            if discount.max_amount:
                discount_amount = min(discount_amount, Decimal(str(discount.max_amount)))
            discount_amount = discount_amount.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            final_price = max(Decimal('0.00'), original_price - discount_amount)
        else:
            final_price = original_price

        final_price = final_price.quantize(Decimal("0.01"), rounding=ROUND_DOWN)

        return final_price, discount_amount, float(discount_percent)

def _get_applicable_discount(user, product, now):
        discount_qs = Discount.objects.filter(
            Q(pricelist__active=True) &
            Q(pricelist__branch__is_main=True) &
            (Q(time_from__lte=now) | Q(time_from__isnull=True)) &
            (Q(time_to__gte=now) | Q(time_to__isnull=True))
        )

        discount = discount_qs.filter(product=product, product__isnull=False).first()
        if discount:
            return discount

        if product.product_template:
            discount = discount_qs.filter(
                product_template=product.product_template,
                product_template__isnull=False,
                product__isnull=True
            ).first()
            if discount:
                return discount

        if product.product_template and product.product_template.category:
            discount = discount_qs.filter(
                category=product.product_template.category,
                category__isnull=False,
                product__isnull=True,
                product_template__isnull=True
            ).first()
            if discount:
                return discount

        if product.product_template and product.product_template.branch:
            discount = discount_qs.filter(
                branch=product.product_template.branch,
                branch__isnull=False,
                product__isnull=True,
                product_template__isnull=True,
                category__isnull=True
            ).first()
            if discount:
                return discount

        return None


@extend_schema_view(
    list=extend_schema(
        summary="List user's order ratings",
        description="Returns a list of all order ratings made by the authenticated user.",
        responses={200: OrderRatingSerializer(many=True)},
    ),
    create=extend_schema(
        summary="Rate an order",
        description="Allows an authenticated user to rate an order they have received.",
        request=OrderRatingSerializer,
        responses={
            201: OrderRatingSerializer,
            400: {"detail": "Invalid data or already rated"},
        },
    ),
)
class OrderRatingViewSet(ModelViewSet):
    queryset = OrderRating.objects.all()
    serializer_class = OrderRatingSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        return self.queryset.filter(reviewer=self.request.user)

    def perform_create(self, serializer):
        serializer.save(reviewer=self.request.user)

    def perform_update(self, serializer):
        # Ensure the reviewer cannot be changed
        serializer.save(reviewer=self.request.user)

    def create(self, request, *args, **kwargs):
        data = super().create(request, *args, **kwargs)
        return Response(
            {"message": _("Order has been rated")}, status=status.HTTP_201_CREATED
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.reviewer == request.user:
            super().destroy(request, *args, **kwargs)
            return Response(
                {"message": _("Order rating has been deleted")}, status=status.HTTP_204_NO_CONTENT
            )
        else:
            return Response({"detail": "You can't delete this order rating."}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    list=extend_schema(
        summary="List promo codes",
        description="Returns promo codes assigned to the authenticated user that are active and within the valid time period.",
        tags=["Promo Codes"],
    ),
    retrieve=extend_schema(
        summary="Retrieve a promo code",
        description="Returns details of a specific promo code assigned to the authenticated user.",
        tags=["Promo Codes"],
    ),
    create=extend_schema(
        summary="Create a promo code (admin only)",
        description="Allows admin users to create a new promo code.",
        tags=["Promo Codes"],
    ),
    update=extend_schema(
        summary="Update a promo code (admin only)",
        description="Allows admin users to update an existing promo code.",
        tags=["Promo Codes"],
    ),
    partial_update=extend_schema(
        summary="Partially update a promo code (admin only)",
        description="Allows admin users to partially update a promo code.",
        tags=["Promo Codes"],
    ),
    destroy=extend_schema(
        summary="Delete a promo code (admin only)",
        description="Allows admin users to delete a promo code.",
        tags=["Promo Codes"],
    ),
)
class PromoCodeViewSet(ModelViewSet):
    serializer_class = PromoCodeSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticated()]
        else:
            return [IsAuthenticated(), IsAdminUserCustom()]

    def get_queryset(self):
        user = self.request.user
        now_time = now().date()

        # Only active and on the correct date promocodes
        queryset = PromoCode.objects.filter(
            active=True
        ).filter(
            Q(expiration_date__gte=now_time)
        )

        queryset = queryset.filter(Q(partner=user) | Q(partner__isnull=True))

        return queryset

class LoyaltyProgramViewSet(ModelViewSet):
    queryset = LoyaltyProgram.objects.all()
    serializer_class = LoyaltyProgramSerializer
    permission_classes = [IsAuthenticated]


class PromoRewardViewSet(ModelViewSet):
    queryset = PromoReward.objects.all()
    serializer_class = PromoRewardSerializer
    permission_classes = [IsAuthenticated]

class DeliveryPriceViewSet(ModelViewSet):
    queryset = DeliveryPrice.objects.all()
    serializer_class = DeliveryPriceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["district"]


class OrderPaymentApiView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Pay for an order",
        description="Processes payment for an order using the given payment method.",
        request=OrderPaymentSerializer,
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Valid payment example",
                value={"order_id": 123, "payment_method": "CARD"},
                request_only=True,
            ),
            OpenApiExample(
                "Success response",
                value={"type": "payment processed successfully"},
                response_only=True,
            ),
            OpenApiExample(
                "Order not found error",
                value={"detail": "Order not found"},
                response_only=True,
                status_codes=["404"],
            ),
        ],
    )
    def post(self, request, *args):
        order_id = request.data.get("order_id")
        method = request.data.get("payment_method")
        print(f"Payment Method: {method}")
        order = Order.objects.filter(pk=order_id, user=request.user).first()
        if not order:
            return Response(
                {"detail": "Order not found"}, status=status.HTTP_404_NOT_FOUND
            )
        if method not in [
            "PAYME",
            "XAZNA",
            "ALIF",
            "BEEPUL",
            "ANORBANK",
            "OSON",
            "UZUM",
            "CLICK",
            "CARD",
            "CASH",
        ]:
            return Response(
                {"detail": "Invalid payment method"}, status=status.HTTP_400_BAD_REQUEST
            )
        accept_language = request.headers.get("Accept-Language", "en")

        balance_amount_used = order.balance_amount or Decimal("0.0")
        promocode_discount = order.promocode_amount or Decimal("0.0")

        if method in [
            "PAYME",
            "XAZNA",
            "ALIF",
            "BEEPUL",
            "ANORBANK",
            "OSON",
            "UZUM",
            "CLICK",
            "CARD",
        ]:
            multicard_url = self._handle_multicard_payment(
                order,
                method,
                accept_language,
                request.data,
                balance_amount_used,
                promocode_discount,
            )
            if not multicard_url["success"]:
                return Response(
                    {"type": method, "detail": multicard_url},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {"type": method, "detail": multicard_url["message"]},
                status=status.HTTP_200_OK,
            )
        else:
            order.payment_method = method
            order.payment_status = "PENDING"
            order.save(update_fields=["payment_method", "payment_status"])
            return Response(
                {
                    "type": method,
                    "detail": "Order created successfully",
                    "order_id": order.id,
                },
                status=status.HTTP_200_OK,
            )

    def _calculate_item_promocode_discount(self, order, order_item, promocode_discount):
        total_item_price = order.total_price

        if total_item_price <= 0 or order_item.total_price <= 0:
            return Decimal("0.00")

        proportion = order_item.total_price / total_item_price
        discount_amount = (promocode_discount * proportion).quantize(Decimal("0.01"))
        return max(Decimal("0.00"), discount_amount)

    def _handle_multicard_payment(
        self,
        order,
        method,
        accept_language,
        request_data,
        balance_amount_used=Decimal("0.0"),
        promocode_discount=Decimal("0.0"),
    ):
        try:
            token_and_store_id = get_token_and_store_id()
            if not token_and_store_id["success"]:
                return {"success": False, "message": "Config is not set"}

            d_token = token_and_store_id["token"]
            store_id = token_and_store_id["store_id"]

            BASE_URL = os.getenv("BASE_URL", "https://api.car-land.uz")
            url = "https://mesh.multicard.uz/payment"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {d_token}",
            }
            
            amount = order.price
            if amount < 500:
                return {
                    "success": False,
                    "message": _(
                        "Amount is less than 500 UZS after cashback deduction"
                    ),
                }

            products_data = []
            
            # Calculate total order value for balance amount distribution (excluding delivery, cashback, coupon items)
            eligible_items = [
                item for item in order.items.all()
                if item.product and item.product.product_type not in ['CASHBACK', 'DELIVERY_PRICE', 'COUPON']
            ]
            
            total_eligible_value = sum(item.total_price for item in eligible_items)
            
            for item in order.items.all():
                # Skip items that shouldn't be sent to Multicard
                if item.product and item.product.product_type not in ['CASHBACK', 'DELIVERY_PRICE', 'COUPON']:
                    mxik = item.product.mxik
                    package_code = item.product.package_code
                    
                    if not mxik:
                        mxik = item.product.product_template.category.mxik
                    if not package_code:
                        package_code = item.product.product_template.category.package_code

                    # Use existing function for promocode distribution
                    item_promocode_discount = self._calculate_item_promocode_discount(
                        order, item, promocode_discount
                    )
                    
                    # Calculate proportional balance amount distribution
                    if total_eligible_value > 0:
                        item_proportion = item.total_price / total_eligible_value
                        item_balance_discount = balance_amount_used * item_proportion
                    else:
                        item_balance_discount = Decimal("0.0")
                    
                    # Get existing item discount
                    item_discount_amount = item.discount_amount if item.discount_amount else Decimal("0.0")
                    
                    # Calculate totals
                    item_price = float(item.total_price)
                    total_discounts = float(
                        item_discount_amount + item_promocode_discount + item_balance_discount
                    )
                    final_item_total = item_price - total_discounts
                    
                    # Ensure we don't have negative totals
                    if final_item_total < 0:
                        final_item_total = 0
                        total_discounts = item_price

                    products_data.append(
                        {
                            "qty": item.quantity,
                            "price": item_price * 100,  # Convert to tiyin
                            "mxik": mxik,
                            "package_code": package_code,
                            "name": item.product.name,
                            "discount": total_discounts * 100,  # Convert to tiyin
                            "other": 0.0,
                            "total": item_price * item.quantity * 100,  # Convert to tiyin
                        }
                    )

            # Add delivery price if exists
            if order.delivery_price > 0:
                delivery_discount  = _calculate_delivery_promocode_discount(order, order.delivery_price, promocode_discount)
                products_data.append(
                    {
                        "qty": 1,
                        "price": float(order.delivery_price * 100),
                        "mxik": "10112006002000000",
                        "package_code": "1209779",
                        "name": "Delivery Price",
                        "discount": float(delivery_discount * 100),
                        "other": 0.0,
                        "total": float(order.delivery_price * 100),
                    }
                )

            uuid_ref = uuid4()
            # Instead of save(), use update()
            Order.objects.filter(pk=order.pk).update(raxmat_reference=uuid_ref, send_odoo=False)
            
            data = {
                "store_id": store_id,
                "amount": float(amount * 100),
                "currency": "UZS",
                "lang": accept_language,
                "invoice_id": str(uuid_ref),
                "callback_url": f"{BASE_URL}/api/multicard/invoice-response/",
                "ofd": products_data,
            }
            
            # Set payment system based on payment method
            payment_system_mapping = {
                "CLICK": "click",
                "UZUM": "uzum", 
                "PAYME": "payme",
                "XAZNA": "xazna",
                "ALIF": "alif",
                "BEEPUL": "beepul",
                "ANORBANK": "anorbank",
                "OSON": "oson"
            }
            
            if method in payment_system_mapping:
                data["payment_system"] = payment_system_mapping[method]

            print(f"Multicard sending URL: {url}\nData: {data}")
            response = requests.post(url, data=json.dumps(data), headers=headers)
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"Multicard response data: {response_data}")
                checkout_url = response_data.get("data", {}).get("checkout_url")
                uuid = response_data.get("data", {}).get("uuid")
                
                # Use update here as well
                Order.objects.filter(pk=order.pk).update(raxmat_payment_id=uuid)
                return {"success": True, "message": checkout_url}
            else:
                return {"success": False, "message": response.json()}
                
        except Exception as e:
            return {"success": False, "message": str(e)}


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def rating_type_list(request):

    status_filter = request.GET.get("status", None)
    search = request.GET.get("search", None)

    # Validate status parameter
    if status_filter and status_filter not in ["good", "bad"]:
        return Response(
            {"error": 'Invalid status parameter. Must be "good" or "bad".'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Base queryset (exclude soft-deleted)
    queryset = RatingType.objects.filter()

    if status_filter:
        queryset = queryset.filter(status=status_filter)

    if search:
        queryset = queryset.filter(
            Q(name_en__icontains=search)
            | Q(name_ru__icontains=search)
            | Q(name_uz__icontains=search)
        )

    # Order by id
    queryset = queryset.order_by("id")

    # Serialize data
    serializer = RatingTypeSerilazier(queryset, many=True, context={"request": request})

    return Response({"results": serializer.data}, status=status.HTTP_200_OK)


def _calculate_item_promocode_discount(order, order_item, promocode_discount):
    total_item_price = order.total_price

    if total_item_price <= 0 or order_item.total_price <= 0:
        return Decimal("0.00")

    proportion = order_item.total_price / total_item_price
    discount_amount = (promocode_discount * proportion).quantize(Decimal("0.01"))
    return max(Decimal("0.00"), discount_amount)


def delayed_update_order(order_id, poll_interval=2):
    pass

    # time.sleep(60)
    # # start_time = time.time()
    
    # try:
    #     order = Order.objects.get(pk=order_id)
    # except Order.DoesNotExist:
    #     print(f"Order with id {order_id} not found")
    #     return
    
    # # Poll until all order items are synced to Odoo or timeout
    # # while time.time() - start_time < max_wait_time:
    # #     order.refresh_from_db()
    # #     order_items = order.items.all()
        
    # #     # Check if all order items have been sent to Odoo
    # #     pending_items = order_items.filter(
    # #         send_odoo=True  # Items that still need to be sent
    # #     ).exclude(
    # #         sync_status='synced'  # Items that are already synced
    # #     )
        
    # #     if not pending_items.exists():
    # #         # All order items have been sent to Odoo, proceed with order update
    # #         break
        
    # #     print(f"Waiting for {pending_items.count()} order items to be sent to Odoo...")
    # # else:
    # #     # Timeout occurred
    # #     print(f"Timeout waiting for order items to be sent to Odoo for order {order_id}")
    
    # # # Proceed with order update regardless of timeout
    # try:
    #     order._run_odoo_operation("update")
    # except Exception as e:
    #     print(f"while sending order {order_id} error: {str(e)}")
    #     pass


def get_check(order, max_retries=20, delay_seconds=5):
    try:
        token_and_store_id = get_token_and_store_id()
        if not token_and_store_id["success"]:
            logger.error("Failed to get token and store ID")
            return False

        token_str = token_and_store_id["token"]
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token_str}",
        }
        payment_url = f"https://mesh.multicard.uz/payment/{order.raxmat_payment_id}/ofd"
        
        balance_amount_used = order.balance_amount or Decimal("0.0")
        promocode_discount = order.promocode_amount or Decimal("0.0")

        products_data = []
        
        # Calculate total order value for balance amount distribution (excluding delivery, cashback, coupon items)
        eligible_items = [
            item for item in order.items.all()
            if item.product and item.product.product_type not in ['CASHBACK', 'DELIVERY_PRICE', 'COUPON']
        ]
        
        total_eligible_value = sum(item.total_price for item in eligible_items)
        
        for item in order.items.all():
            if item.product and item.product.product_type not in ["CASHBACK", "DELIVERY_PRICE", "COUPON"]:
                mxik = item.product.mxik or (
                    item.product.product_template.category.mxik
                    if hasattr(item.product, "product_template")
                    and hasattr(item.product.product_template, "category")
                    and item.product.product_template.category
                    else None
                )
                package_code = item.product.package_code or (
                    item.product.product_template.category.package_code
                    if hasattr(item.product, "product_template")
                    and hasattr(item.product.product_template, "category")
                    and item.product.product_template.category
                    else None
                )

                # Calculate promocode discount for this item
                item_promocode_discount = _calculate_item_promocode_discount(
                    order, item, promocode_discount
                )
                
                # Calculate proportional balance amount distribution
                if total_eligible_value > 0:
                    item_proportion = item.total_price / total_eligible_value
                    item_balance_discount = balance_amount_used * item_proportion
                else:
                    item_balance_discount = Decimal("0.0")

                # Get existing item discount
                item_discount_amount = item.discount_amount if item.discount_amount else Decimal("0.0")
                
                # Calculate totals
                item_price = float(item.total_price)
                total_discounts = float(
                    item_discount_amount + item_promocode_discount + item_balance_discount
                )
                final_item_total = item_price - total_discounts
                
                # Ensure we don't have negative totals
                if final_item_total < 0:
                    final_item_total = 0
                    total_discounts = item_price

                products_data.append(
                    {
                        "qty": item.quantity,
                        "price": item_price * 100,  # Convert to tiyin
                        "mxik": mxik,
                        "package_code": package_code,
                        "name": item.product.name,
                        "discount": total_discounts * 100,  # Convert to tiyin
                        "other": 0.0,
                        "total": item_price * item.quantity * 100,  # Convert to tiyin
                    }
                )

        # Add delivery price if exists
        if order.delivery_price > 0:
            delivery_discount  = _calculate_delivery_promocode_discount(order, order.delivery_price, promocode_discount)
            products_data.append(
                {
                    "qty": 1,
                    "price": float(order.delivery_price * 100),
                    "mxik": "10112006002000000",
                    "package_code": "1209779",
                    "name": "Delivery Price",
                    "discount": float(delivery_discount * 100),
                    "other": 0.0,
                    "total": float(order.delivery_price * 100),
                }
            )

        data = {
            "card_amount": float((order.price) * 100),
            "cash_amount": float(0),
            "ofd": products_data,
        }
        print(f"\n\n\n\n\n\n\nData: {data}\n\n\n\n\n\n\n")
        
        for attempt in range(max_retries):
            if order.payment_status == "COMPLETED":
                response = requests.patch(payment_url, json=data, headers=headers)
                try:
                    response_data = response.json()
                except ValueError:
                    logger.error("Invalid JSON response")
                    return False

                tax = response_data.get("data", {})
                print(f"Attempt {attempt+1}: Response data: {response_data}")

                if tax:
                    qr_url = tax.get("qr_url")
                    f_num = tax.get("f_num")
                    fm_num = tax.get("fm_num")

                    if qr_url and f_num and fm_num:
                        order.fiscal_url = qr_url
                        order.f_num = f_num
                        order.fm_num = fm_num
                        order.send_odoo = False
                        order.payment_status = "COMPLETED"
                        order.save(update_fields=["fiscal_url","send_odoo","payment_status", "f_num", "fm_num"])
                        return True
                    else:
                        logger.warning("Tax found but missing required fields")
                        return False

                logger.info(f"Tax not found, retrying... ({attempt+1}/{max_retries})")
            time.sleep(delay_seconds)

        logger.error("Max retries reached, tax object not found")
        return False

    except Exception as e:
        logger.error(f"Error fetching check data: {str(e)}")
        return False