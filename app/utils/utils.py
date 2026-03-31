import base64
import json
import logging
import mimetypes
from decimal import Decimal

import requests
from django.conf import settings

from app.models.log_connection import OdooConnectorLogger

logger = logging.getLogger(__name__)

# getting odoo api url from settings
odoo_url = settings.ODOO_API_URL


def encode_file_to_base64_with_mime(file_field):
    """
    Encode a file to base64 with its mime type
    """
    if file_field and hasattr(file_field, "path"):
        mime_type, _ = mimetypes.guess_type(file_field.path)
        with open(file_field.path, "rb") as file:
            encoded_string = base64.b64encode(file.read()).decode("utf-8")
            return f"data:{mime_type};base64,{encoded_string}"
    return None


class OdooSync:
    import json
    import logging

    # Odoo loglarini chiroyli formatda chiqarish uchun logger sozlamasi
    logger = logging.getLogger(__name__)

    @staticmethod
    def send_to_odoo(model_name, instance, odoo_id_field="odoo_id"):
        logger_manager = OdooConnectorLogger(
            operation_type="update",
            model_name=model_name,
            local_model=instance.__class__.__name__,
            instance_id=instance.pk,
            odoo_id=getattr(instance, odoo_id_field),
        )
        print(f"\n\n\n Updating  {model_name}\n\n\n")


        with logger_manager.log_operation():
            if not getattr(instance, odoo_id_field) or not hasattr(
                instance, "prepare_odoo_data"
            ):
                logger.debug(
                    f"[{model_name}] {instance.__class__.__name__} - No odoo_id or prepare_odoo_data"
                )
                return False

            odoo_prop, url = instance.prepare_odoo_data()

            # Log for prepared data, format with indent for better readability
            logger.debug(
                f"[{model_name}] Prepared odoo data: {json.dumps(odoo_prop, indent=4)}"
            )

            if not odoo_prop:
                logger.debug(
                    f"[{model_name}] {instance.__class__.__name__} - No data to send"
                )
                return False

            payload = {
                "model": model_name,
                "e_id": getattr(instance, odoo_id_field),
                "data": odoo_prop,
            }
            logger_manager.update_response({"request_payload": payload})

            response = requests.post(
                url=f"{odoo_url}/api/update/{url}",
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            response_data = response.json()

            # Log the response data with indent
            logger.debug(
                f"[{model_name}] Response from Odoo: {json.dumps(response_data, indent=4)}"
            )

            logger_manager.update_response(response_data)
            return True

    @staticmethod
    def create_to_odoo(model_name, instance):
        logger_manager = OdooConnectorLogger(
            operation_type="create",
            model_name=model_name,
            local_model=instance.__class__.__name__,
            instance_id=instance.pk,
            odoo_id=instance.odoo_id,
        )
        print(f" \n\n\n Creating  {model_name}\n\n\n")

        with logger_manager.log_operation():
            if not hasattr(instance, "prepare_odoo_data"):
                logger.debug(
                    f"[{model_name}] {instance.__class__.__name__} - No prepare_odoo_data method"
                )
                return False

            odoo_prop, url = instance.prepare_odoo_data()

            # Log for prepared data, format with indent for better readability
            logger.debug(
                f"[{model_name}] Prepared odoo data: {json.dumps(odoo_prop, indent=4)}"
            )

            if not odoo_prop:
                logger.debug(
                    f"[{model_name}] {instance.__class__.__name__} - No data to send"
                )
                return False
            if model_name == "sale.order.line" and odoo_prop['price_unit'] <= 0 and instance.product and instance.product.product_type == "COUPON":
                odoo_prop["e_id"] = instance.order.promocode.odoo_id if instance.order and instance.order.promocode and instance.order.promocode.odoo_id else None
            else:
                odoo_prop["e_id"] = instance.odoo_id
            payload = {"model": model_name, "data": odoo_prop}

            logger_manager.update_response({"request_payload": payload})

            response = requests.post(
                url=f"{odoo_url}/api/create/{url}",
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            response_data = response.json()
            print("\n\n\n\n\n\n\n\n\n\n")
            try:
                from app.models.order import Order
                if url == "sale_order":
                    # print(f"\norder CREATE keldi {response_data}\n")
                    instance.name = response_data.get("result", {}).get("name", "No order name")
                    instance.send_odoo = False
                    instance.save()
                if url == "sale-order-line":
                    try:
                        instance.send_odoo = False
                        instance.sended_to_odoo = True
                        instance.save()
                        
                        # Check if all order items are sent and trigger order update if ready
                        order = Order.objects.get(pk=instance.order.pk)
                        if order:
                            items =  order.items.filter(sended_to_odoo=True).count()
                            print(f"\n\n\n{items}\n\n\n")
                            # Check if all items are sent and payment is complete
                            is_correct = True if  items==order.total_items_count and order.payment_status == "COMPLETED" else False
                            print(f"\n\n\n{is_correct}\n\n\n")
                            print(f"\n\n{order.total_items_count}\n\n")
                            if (items==order.total_items_count and
                                order.payment_status == "COMPLETED"):
                                try:
                                    print(f"All order items sent for order {order.id}, triggering order update")
                                    result = order._run_odoo_operation("update")
                                    print(f"\n\n\n{result}\n\n\n")
                                except Exception as e:
                                    print(f"Error updating order {order.id}: {str(e)}")
                    except Order.DoesNotExist:
                        pass
                    except Exception as e:
                        print(f"\n\n\n{str(e)}\n\n")
                        pass

            except Exception as e:
                print(f"Error while updating order name: {e}")
            print("\n\n\n\n\n\n\n\n\n\n")

            # Log the response data with indent
            logger.debug(
                f"[{model_name}] Response from Odoo: {json.dumps(response_data, indent=4)}"
            )

            logger_manager.update_response(response_data)

            instance.send_odoo = False
            instance.sync_status = "synced"
            instance.save()
            return True

    @staticmethod
    def send_to_odoo_delete(model_name, instance, odoo_id_field="odoo_id"):
        logger_manager = OdooConnectorLogger(
            operation_type="delete",
            model_name=model_name,
            local_model=instance.__class__.__name__,
            instance_id=instance.pk,
            odoo_id=getattr(instance, odoo_id_field),
        )

        with logger_manager.log_operation():
            payload = {
                "model": model_name,
                "e_id": getattr(instance, odoo_id_field),
            }

            logger_manager.update_response({"request_payload": payload})

            # Log payload being sent to Odoo in a formatted way
            logger.debug(
                f"[{model_name}] Payload to delete: {json.dumps(payload, indent=4)}"
            )

            response = requests.post(
                url=f"{odoo_url}/connect/delete/django_to_odoo",
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            response_data = response.json()

            # Log the response data with indent
            logger.debug(
                f"[{model_name}] Response from Odoo: {json.dumps(response_data, indent=4)}"
            )

            logger_manager.update_response(response_data)
            return True

    @staticmethod
    def prepare_user_data(user_instance, user_info):

        # Handle potential None values for first_name and last_name
        first_name = user_info.first_name if user_info and user_info.first_name else ""
        last_name = user_info.last_name if user_info and user_info.last_name else ""
        name = f"{first_name} {last_name}".strip()
        cleaned_phone = (
            user_instance.phone.replace("+", "") if user_instance.phone else ""
        )
        email = f"{cleaned_phone}@gmail.com" if cleaned_phone else ""
        referral_link = user_info.referral_link if user_info and user_info.referral_link else ""
        referral_count = user_info.referral_count if user_info and user_info.referral_count else 0
        is_referred = user_info.is_referred if user_info and hasattr(user_info, 'is_referred') else False

        data = {
            "e_id": user_instance.odoo_id if user_instance.odoo_id else None,
            "name": name if name else " ",
            # "login": email if email else None,
            "email": email if email else None,
            "phone": user_instance.phone if user_instance.phone else None,
            "address": user_info.address if user_info and user_info.address else "",
            "image": (
                encode_file_to_base64_with_mime(user_info.avatar)
                if user_info and user_info.avatar
                else None
            ),
            "is_updated": False,
            "send_odoo": True,
            "referral_link": referral_link,
            "referral_count": referral_count,
            "is_referred": is_referred,
        }

        return data, "portal_user"

    @staticmethod
    def prepare_product_data(product):
        data = {
            "e_id": product.odoo_id,
            "product_tmpl_id": (
                product.product_template.odoo_id if product.product_template else None
            ),
            "product_template_attribute_value_ids": [
                attribute.odoo_id
                for attribute in product.attributes.all()
                if attribute.odoo_id
            ],
            # 'description': product.description,'
            # 'image': product.image.url if product.image else None,
            # 'amount': float(product.amount) if product.amount is not None else None,
            # 'is_top': product.is_top,
            "image": (
                encode_file_to_base64_with_mime(product.image)
                if product.image
                else None
            ),
            "mxik": product.mxik if product.mxik else None,
            "package_code": product.package_code if product.package_code else None,
            "create_date": (
                product.created_at.isoformat() if product.created_at else None
            ),
            "write_date": (
                product.updated_at.isoformat() if product.updated_at else None
            ),
            "is_updated": False,
            "send_odoo": True,
        }

        return data, "product_product"

    @staticmethod
    def prepare_branch_data(branch_instance):

        data = {
            "e_id": branch_instance.odoo_id if branch_instance.odoo_id else None,
            "name": branch_instance.name if branch_instance.name else "",
            "name_ru":branch_instance.name_ru if branch_instance.name_ru else "",
            "name_uz":branch_instance.name_uz if branch_instance.name_uz else "",
            "parent_id": (
                branch_instance.parent_branch.odoo_id
                if branch_instance.parent_branch
                and branch_instance.parent_branch.odoo_id
                else None
            ),
            "category": branch_instance.category if branch_instance.category else "",
            # "contacts": branch_instance.contacts if branch_instance.contacts else "",
            "image": (
                encode_file_to_base64_with_mime(branch_instance.image)
                if branch_instance.image
                else None
            ),
            "branch_type": branch_instance.branch_type,
            "phone": branch_instance.phone if branch_instance.phone else "",
            "latitude": branch_instance.latitude if branch_instance.latitude else "",
            "longitude": branch_instance.longitude if branch_instance.longitude else "",
            "google_map": (
                branch_instance.google_link if branch_instance.google_link else ""
            ),
            "yandex_map": (
                branch_instance.yandex_link if branch_instance.yandex_link else ""
            ),
            "is_updated": False,
            "send_odoo": True,
        }

        return data, "company"

    @staticmethod
    def prepare_brand_data(brand):
        data = {
            "e_id": brand.odoo_id if brand.odoo_id else None,
            "name_uz": brand.name_uz if brand.name_uz else "No name in uz",
            "name_ru": brand.name_ru if brand.name_ru else "No name in ru",
            "name_en": brand.name_en if brand.name_en else "No name in en",
            "image": (
                encode_file_to_base64_with_mime(brand.image) if brand.image else None
            ),
            "is_top": brand.is_top,
            "is_updated": False,
            "send_odoo": True,
        }

        return data, "product_brand"

    @staticmethod
    def perpare_oil_change_rating(oil_change):
        option_ids = list(oil_change.options_ids.values_list("odoo_id", flat=True))
        data = {
            "e_id": oil_change.odoo_id,
            "reviewer_id": (
                oil_change.reviewer.odoo_id
                if oil_change.reviewer and oil_change.reviewer.odoo_id
                else None
            ),
            "oil_change_id": (
                oil_change.oil_change_id.odoo_id
                if oil_change.oil_change_id and oil_change.oil_change_id.odoo_id
                else None
            ),
            "rating": oil_change.rating,
            "description": oil_change.description,
            "option_ids": option_ids,
        }
        return data, "oil_change_rating"

    @staticmethod
    def prepate_rating(rating):
        data = {
        }
        return  data,"rating_type"

    @staticmethod
    def prepare_template_image(product_image):
        data = {
            "image":encode_file_to_base64_with_mime(product_image.image) if product_image.image else None,
            "product_tmpl_id":product_image.product_template.odoo_id if product_image.product_template and product_image.product_template.odoo_id else None,
            "e_id":product_image.odoo_id
        }
        return  data,"product_image"

    @staticmethod
    def prepare_product_rating(product_rating):
        data = {
            "e_id": product_rating.odoo_id,
            "reviewer_id": (
                product_rating.reviewer.odoo_id
                if product_rating.reviewer and product_rating.reviewer.odoo_id
                else None
            ),
            "product_id": (
                product_rating.product.odoo_id
                if product_rating.product and product_rating.product.odoo_id
                else None
            ),
            "rating": product_rating.rating,
            "description": product_rating.description,
        }
        return {k: v for k, v in data.items() if v is not None}, "product_rating"

    @staticmethod
    def prepare_order_rating(order_rating):
        option_ids = list(order_rating.options_ids.values_list("odoo_id", flat=True))
        data = {
            "e_id": order_rating.odoo_id,
            "reviewer_id": (
                order_rating.reviewer.odoo_id
                if order_rating.reviewer and order_rating.reviewer.odoo_id
                else None
            ),
            "order": (
                order_rating.order.odoo_id
                if order_rating.order and order_rating.order.odoo_id
                else None
            ),
            "rating": order_rating.rating,
            "description": order_rating.description,
            "option_ids": option_ids,
        }
        return {k: v for k, v in data.items() if v is not None}, "order_rating"

    @staticmethod
    def prepare_wareHouse_data(werehouse):
        data = {
            "e_id": werehouse.odoo_id if werehouse.odoo_id else None,
            "name": werehouse.name if werehouse.name else "",
            "code": werehouse.code if werehouse.code else "",
            "company_id": (
                werehouse.branch.odoo_id
                if werehouse.branch and werehouse.branch.odoo_id
                else ""
            ),
            "active": True,
            "is_updated": False,
            "send_odoo": True,
        }

        return data, "warehouse"

    @staticmethod
    def prepare_location_data(location):
        company_id = (
            location.warehouse.branch.odoo_id
            if location.warehouse
            and location.warehouse.branch
            and location.warehouse.branch.odoo_id
            else None
        )
        data = {
            "e_id": location.odoo_id if location.odoo_id else None,
            "name": location.name if location.name else "",
            "complete_name": location.complete_name if location.complete_name else "",
            "usage": location.location_type if location.location_type else "",
            "warehouse_id": (
                location.warehouse.odoo_id
                if location.warehouse and location.warehouse.odoo_id
                else ""
            ),
            "location_id": (
                location.parent_location.odoo_id
                if location.parent_location and location.parent_location.odoo_id
                else ""
            ),
            "company_id": company_id,
            "active": True,
            "is_updated": False,
            "send_odoo": True,
        }

        return data, "location"

    @staticmethod
    def prepare_variant_data(variant):
        data = {
            "e_id": variant.odoo_id if variant.odoo_id else None,
            "name": variant.name,
            "is_updated": False,
            "send_odoo": True,
        }

        return data, "django_to_odoo"

    @staticmethod
    def prepare_option_data(option):
        data = {
            "e_id": option.odoo_id if option.odoo_id else None,
            "name": option.name if option.name else "",
            "attribute_id": (
                option.variant.odoo_id
                if option.variant and option.variant.odoo_id
                else None
            ),
            "is_updated": False,
            "send_odoo": True,
        }
        return data, "product_attribute_value"

    @staticmethod
    def perpare_product_option_data(productOption):
        data = {
            "product_template_attribute_value_e_id": productOption.odoo_id,
            "price_extra": (
                float(productOption.additional_price)
                if productOption.additional_price is not None
                else 0.0
            ),
            "is_updated": False,
            "send_odoo": True,
        }
        return data, "product_template_attribute_value_price_extra"

    @staticmethod
    def perpare_product_variant_data(product_variant):
        data = {
            "e_id": product_variant.odoo_id,
            "product_tmpl_id": (
                product_variant.product_template.odoo_id
                if product_variant.product_template
                else None
            ),
            "attribute_id": (
                product_variant.variant.odoo_id if product_variant.variant else None
            ),
            "value_ids": [
                option.odoo_id
                for option in product_variant.product_options.all()
                if option.odoo_id
            ],
            "is_updated": False,
            "send_odoo": True,
        }
        print(f"{data=}")
        return data, "product_template_attribute_line"

    @staticmethod
    def prepare_product_template_data(product_template):
        data = {
            "e_id": product_template.odoo_id,
            "name": product_template.name,
            # 'image': product_template.image.url if product_template.image else None,
            "list_price": (
                float(product_template.price)
                if product_template.price is not None
                else None
            ),
            # 'on_hand': product_template.on_hand,
            "description": product_template.description,
            # "image": encode_file_to_base64_with_mime(product_template.image) if product_template.image else None,
            "categ_id": (
                product_template.category.odoo_id if product_template.category else None
            ),
            "brand_id": (
                product_template.brand.odoo_id if product_template.brand else None
            ),
            # "branch": product_template.branch.odoo_id if product_template.branch else None,
            "create_date": (
                product_template.created_at.isoformat()
                if product_template.created_at
                else None
            ),
            "write_date": (
                product_template.updated_at.isoformat()
                if product_template.updated_at
                else None
            ),
            "is_updated": False,
            "send_odoo": True,
            "is_visible":product_template.is_visible
        }
        return data, "product_template"

    @staticmethod
    def prepare_category_data(category):
        data = {
            "e_id": category.odoo_id if category.odoo_id else None,
            "name": category.name_en if category.name_en else None,
            "name_uz": category.name_uz if category.name_uz else None,
            "name_ru": category.name_ru if category.name_ru else None,
            "parent_id": category.parent.odoo_id if category.parent else None,
            "mxik": category.mxik if category.mxik else None,
            "image": (
                encode_file_to_base64_with_mime(category.image)
                if category.image
                else None
            ),
            "package_code": category.package_code if category.package_code else None,
            "is_updated": False,
            "send_odoo": True,
            "is_visible":category.is_visible
        }

        return data, "product_category"

    @staticmethod
    def prepare_stuck_quant_data(stock_quant):
        data = {
            "e_id": stock_quant.odoo_id if stock_quant.odoo_id else None,
            "product_id": (
                stock_quant.product.odoo_id
                if stock_quant.product and stock_quant.product.odoo_id
                else None
            ),
            "location_id": (
                stock_quant.location.odoo_id
                if stock_quant.location and stock_quant.location.odoo_id
                else None
            ),
            "quantity": (
                float(stock_quant.quantity) if stock_quant.quantity is not None else 0.0
            ),
            "in_date": stock_quant.in_date.isoformat() if stock_quant.in_date else None,
            "is_updated": False,
            "send_odoo": True,
        }
        return data, "stock_quant"

    @staticmethod
    def prepare_pricelist_data(pricelist):
        data = {
            "e_id": pricelist.odoo_id if pricelist.odoo_id else None,
            "name": pricelist.name,
            "currency_id": (
                pricelist.currency.odoo_id
                if pricelist.currency and pricelist.currency.odoo_id
                else None
            ),
            "company_id": (
                pricelist.branch.odoo_id
                if pricelist.branch and pricelist.branch.odoo_id
                else None
            ),
            "active": True,
            "is_updated": False,
            "send_odoo": True,
        }
        return data, "pricelist"

    @staticmethod
    def prepare_currency_data(currency):
        data = {
            "e_id": currency.odoo_id if currency.odoo_id else None,
            "name": currency.name,
            "symbol": currency.symbol,
            "rate": float(currency.rate) if currency.rate is not None else 0.0,
            "active": True,
            "is_updated": False,
            "send_odoo": True,
        }
        return data, "res_currency"

    @staticmethod
    def prepare_discount_data(pricelist_item):
        data = {
            "e_id": pricelist_item.odoo_id if pricelist_item.odoo_id else None,
            "pricelist_id": (
                pricelist_item.pricelist.odoo_id
                if pricelist_item.pricelist and pricelist_item.pricelist.odoo_id
                else None
            ),
            "product_tmpl_id": (
                pricelist_item.product_template.odoo_id
                if pricelist_item.product_template
                and pricelist_item.product_template.odoo_id
                else None
            ),
            "min_quantity": (
                float(pricelist_item.quantity)
                if pricelist_item.quantity is not None
                else 0.0
            ),
            "fixed_price": (
                float(pricelist_item.amount)
                if pricelist_item.amount is not None
                else 0.0
            ),
            "is_updated": False,
            "send_odoo": True,
        }
        return data, "pricelist-item"

    @staticmethod
    def prepare_region_data(region):
        data = {
            "e_id": region.odoo_id if region.odoo_id else None,
            "name": region.name,
            "is_updated": False,
            "send_odoo": True,
        }
        return data, "region"

    @staticmethod
    def prepare_district_data(district):
        data = {
            "e_id": district.odoo_id if district.odoo_id else None,
            "name": district.name,
            "regions_id": (
                district.region.odoo_id
                if district.region and district.region.odoo_id
                else None
            ),
            "is_updated": False,
            "send_odoo": True,
        }
        return data, "district"

    @staticmethod
    def prepare_delivery_price_data(delivery_price):
        data = {
            "e_id": delivery_price.odoo_id if delivery_price.odoo_id else None,
            "district_id": (
                delivery_price.district.odoo_id
                if delivery_price.district and delivery_price.district.odoo_id
                else None
            ),
            "price": (
                float(delivery_price.price) if delivery_price.price is not None else 0.0
            ),
            "is_updated": False,
            "send_odoo": True,
        }
        return data, "delivery_price"

    @staticmethod
    def prepare_oil_brand_data(oil_brand):
        data = {
            "e_id": oil_brand.odoo_id if oil_brand.odoo_id else None,
            "name": oil_brand.name,
            "is_updated": False,
            "send_odoo": True,
        }
        return data, "django_to_odoo"

    @staticmethod
    def prepare_filter_brand_data(filter_brand):
        data = {
            "e_id": filter_brand.odoo_id if filter_brand.odoo_id else None,
            "name": filter_brand.name,
            "description": filter_brand.description,
            "is_updated": False,
            "send_odoo": True,
        }
        return data, "django_to_odoo"

    @staticmethod
    def prepare_booking_data(booking):
        data = {
            "name": booking.name if booking.name else "Booking",
            "e_id": booking.odoo_id if booking.odoo_id else None,
            # "branch_id": booking.branch.odoo_id if booking.branch and booking.branch.odoo_id else None,
            "car_id": (
                booking.car.odoo_id if booking.car and booking.car.odoo_id else "car1"
            ),
            "start": (
                booking.start_time.strftime("%Y-%m-%d %H:%M:%S")
                if booking.start_time
                else "2025-05-24 09:00:00"
            ),
            "stop": (
                booking.end_time.strftime("%Y-%m-%d %H:%M:%S")
                if booking.end_time
                else "2025-05-24 10:00:00"
            ),
            # "status": booking.status,
            "description": booking.notes if booking.notes else "dhjghasd",
            "source": booking.source if booking.source else "WEB",
            "appointment_type_id": (
                booking.appointment.odoo_id
                if booking.appointment and booking.appointment.odoo_id
                else "abc"
            ),
            "resource_ids": (
                [booking.resource.odoo_id]
                if booking.resource and booking.resource.odoo_id
                else ["r1"]
            ),
        }
        print("\n\n\n\n\n\n\n\n\n\n\n")
        print(f"{data=}")
        print("\n\n\n\n\n\n\n\n\n\n\n")
        return data, "booking"

    @staticmethod
    def prepare_firm_data(firm):
        data = {
            "e_id": firm.odoo_id if firm.odoo_id else None,
            "name": firm.name,
            "is_updated": False,
            "send_odoo": True,
        }
        return data, "car_brand"
    
    @staticmethod
    def prepare_request_form_data(request_form):
        source_page_url = f"https://carland.uz/pages/{request_form.source_page.slug}" if request_form.source_page else ""

        data = {
            "name": request_form.name if request_form.name else "",
            "phone": request_form.phone,
            "email": request_form.email if request_form.email else "",
            "source": request_form.source,
            "organization": request_form.organization if request_form.organization else "",
            "description": request_form.commentary if request_form.commentary else "",
            "referred": source_page_url if source_page_url else "",
        }
        return data, "request_form"

    @staticmethod
    def prepare_car_model_data(car_model):
        data = {
            "e_id": car_model.odoo_id if car_model.odoo_id else None,
            "name": car_model.name,
            "car_brand_id": (
                car_model.firm.odoo_id
                if car_model.firm and car_model.firm.odoo_id
                else None
            ),
            "is_updated": False,
            "send_odoo": True,
        }
        return data, "cashback_cars"

    @staticmethod
    def prepare_some_color_data(some_color):
        data = {
            "e_id": some_color.odoo_id if some_color.odoo_id else None,
            "name_en": some_color.name_en,
            "name_uz": some_color.name_uz,
            "name_ru": some_color.name_ru,
            "color_code": some_color.color_code,
            "is_updated": False,
            "send_odoo": True,
        }
        return data, "some_color"

    @staticmethod
    def prepare_car_color_data(car_color):
        data = {
            "e_id": car_color.odoo_id if car_color.odoo_id else None,
            "color_id": (
                car_color.some_color.odoo_id
                if car_color.some_color and car_color.some_color.odoo_id
                else None
            ),
            "image": (
                encode_file_to_base64_with_mime(car_color.image)
                if car_color.image
                else None
            ),
            "car_id": (
                car_color.car_model.odoo_id
                if car_color.car_model and car_color.car_model.odoo_id
                else None
            ),
            "is_updated": False,
            "send_odoo": True,
        }
        return data, "car_color"

    @staticmethod
    def prepare_car_data(car):
        computed_name = f"{car.model.name} [{car.number}]"
        data = {
            "e_id": car.odoo_id if car.odoo_id else None,
            "name": computed_name,
            "parent_e_id": car.user.odoo_id if car.user and car.user.odoo_id else None,
            "car_brand_e_id": (
                car.firm.odoo_id if car.firm and car.firm.odoo_id else None
            ),
            "car_model_e_id": (
                car.model.odoo_id if car.model and car.model.odoo_id else None
            ),
            "car_color_e_id": (
                car.color.odoo_id if car.color and car.color.odoo_id else None
            ),
            "car_number": car.number,
            # "last_oil_change": car.oil_change_history,
            "is_updated": False,
            "send_odoo": True,
        }
        return data, "car"

    @staticmethod
    def prepare_oil_changed_history_data(oil_changed_history):
        data = {
            "e_id": (
                oil_changed_history.odoo_id if oil_changed_history.odoo_id else None
            ),
            "car_id": (
                oil_changed_history.car.odoo_id
                if oil_changed_history.car and oil_changed_history.car.odoo_id
                else None
            ),
            "oil_brand_id": (
                oil_changed_history.oil_brand.odoo_id
                if oil_changed_history.oil_brand
                and oil_changed_history.oil_brand.odoo_id
                else None
            ),
            "last_oil_change": (
                oil_changed_history.last_oil_change.strftime("%Y-%m-%d %H:%M:%S")
                if oil_changed_history.last_oil_change
                else "2025-05-24 09:00:00"
            ),
            "distance_driven": oil_changed_history.distance if oil_changed_history.distance else 0,
            "recommended_distance": oil_changed_history.recommended_distance,
            "daily_distance": oil_changed_history.daily_distance,
            "source": oil_changed_history.source if oil_changed_history.source else None,
            "is_updated": False,
            "send_odoo": True,
        }
        return data, "oil_change_history"

    @staticmethod
    def prepare_order_data(order):
        get_state = None
        if order.status == "CANCELLED":
            get_state = "cancel"
        elif order.status == "COMPLETED":
            get_state = "sale"
        elif order.status == "PENDING":
            get_state = "draft"
        else:
            get_state = "sent"
        if order.car:
            partner_id = order.car.odoo_id if order.car and order.car.odoo_id else None
        else:
            partner_id = order.user.odoo_id if order.user and order.user.odoo_id else None
        # # TODO REMOVE THIS LINE AFTER TESTING
        # get_state = "sale"
        data = {
            "e_id": order.odoo_id if order.odoo_id else None,
            "partner_id": partner_id,
            "state": get_state,
            "c_order_type": "take_away" if order.type == "PICKUP" else "delivery",
            "source_id": order.source,
            "amount_total": float(order.price) if order.price is not None else 0.0,
            "pricelist_id": (
                order.pricelist.odoo_id
                if order.pricelist and order.pricelist.odoo_id
                else None
            ),
            # "created_at": order.created_at.isoformat() if order.created_at else None,
            # "updated_at": order.updated_at.isoformat() if order.updated_at else None,
            # "description": order.description if order.description else "",
            # "completed_at": order.completed_at.isoformat() if order.completed_at else None,
            # "cancelled_at": order.cancelled_at.isoformat() if order.cancelled_at else None,
            # "region_id": order.region.odoo_id if order.region and order.region.odoo_id else None,
            # "district_id": order.district.odoo_id if order.district and order.district.odoo_id else None,
            "amount_delivery": (
                float(order.delivery_price) if order.delivery_price is not None else 0.0
            ),
            "address_id": order.address_id.odoo_id if order.address_id and order.address_id.odoo_id else None,
            "promocode_id": (
                order.promocode.odoo_id
                if order.promocode and order.promocode.odoo_id
                else None
            ),
            "note": order.description if order.description else None,
            # "pickup_time": order.pickup_time.isoformat() if order.pickup_time else None,
            "raxmat_reference": order.raxmat_reference if order.raxmat_reference else None,
            "uuid": order.raxmat_payment_id if order.raxmat_payment_id else None,
            "qr_url": order.fiscal_url if order.fiscal_url else None,
            "f_num": order.f_num if order.f_num else None,
            "fm_num": order.fm_num if order.fm_num else None,
            # "payment_time": order.payment_time.isoformat() if order.payment_time else None,
            "payment_status": order.payment_status if order.payment_status else None,
            # "delivery_type": order.delivery_type if order.delivery_type else None,
            "payment_method": order.payment_method if order.payment_method else None,
            "branch_id": (
                order.branch.odoo_id if order.branch and order.branch.odoo_id else None
            ),
            "is_updated": False,
            "send_odoo": True,
        }
        print(f"\n\n\nOrder Data{data=}\n\n\n")
        return data, "sale_order"

    @staticmethod
    def prepare_order_line_data(order_line):
        data = {
            "e_id": order_line.odoo_id if order_line.odoo_id else None,
            "order_id": (
                order_line.order.odoo_id
                if order_line.order and order_line.order.odoo_id
                else None
            ),
            "product_id": (
                order_line.product.odoo_id
                if order_line.product and order_line.product.odoo_id
                else None
            ),
            "product_uom_qty": (
                float(order_line.quantity) if order_line.quantity is not None else 0.0
            ),
            "price_unit": (
                float(order_line.price) if order_line.price is not None else 0.0
            ),
            "price_subtotal": (
                float(order_line.total_price)
                if order_line.total_price is not None
                else 0.0
            ),
            "is_updated": False,
            "send_odoo": True,
        }
        return data, "sale-order-line"

    @staticmethod
    def prepare_address_data(address):

        data = {
            "e_id": address.odoo_id if address.odoo_id else None,
            "type": "delivery",  # this is address, so it will be delivery type
            "company_type": "person",
            "name": address.name if address.name else "",
            "parent_id": (
                address.user.odoo_id if address.user and address.user.odoo_id else None
            ),
            "region_id": (
                address.region.odoo_id
                if address.region and address.region.odoo_id
                else None
            ),
            "district_id": (
                address.district.odoo_id
                if address.district and address.district.odoo_id
                else None
            ),
            "yandex_link": address.yandex_link if address.yandex_link else None,
            "street": address.additional if address.additional else "",
            "street2": (
                f"{address.building} {address.floor}"
                if address.building and address.floor
                else ""
            ),
            "is_updated": False,
            "send_odoo": True,
        }
        return data, "user_delivery_address"
    @staticmethod
    def prepare_balance_status_data(balance_status):
        data = {
            "e_id": balance_status.odoo_id or None,
            "name": balance_status.name,
            "percentage": (
                float(balance_status.percentage)
                if isinstance(balance_status.percentage, Decimal)
                else balance_status.percentage
            ),
            "minimum_amount": (
                float(balance_status.minimum_amount)
                if isinstance(balance_status.minimum_amount, Decimal)
                else balance_status.minimum_amount
            ),
            "next_minimum_amount": (
                float(balance_status.next_minimum_amount)
                if isinstance(balance_status.next_minimum_amount, Decimal)
                else balance_status.next_minimum_amount
            ),
            "num": int(balance_status.num),
            "time_line": balance_status.time_line,
            "description_en": balance_status.description_en,
            "icon": (
                encode_file_to_base64_with_mime(balance_status.icon)
                if balance_status.icon
                else None
            ),
            "is_updated": False,
            "send_odoo": True,
        }
        return data, "balance-status"

    # @staticmethod
    # def prepare_loyalty_program_data(loyalty_program):
    #     data = {
    #         "e_id": loyalty_program.odoo_id or None,
    #         "name": loyalty_program.name,
    #         "program_type": loyalty_program.program_type,
    #         "branch": loyalty_program.branch.odoo_id if loyalty_program.branch else None,
    #         "currency": loyalty_program.currency.odoo_id if loyalty_program.currency else None,
    #         "active": loyalty_program.active,
    #         "date_from": loyalty_program.date_from,
    #         "date_to": loyalty_program.date_to,
    #         "limit_usage": loyalty_program.limit_usage,
    #         "max_usage": loyalty_program.max_usage,
    #         "is_updated": False,
    #         "send_odoo": True,
    #     }
    #     return data, "loyalty_program"

    # @staticmethod
    # def prepare_promo_reward_data(promo_reward):
    #     data = {
    #         "e_id": promo_reward.odoo_id or None,
    #         "reward_type": promo_reward.reward_type,
    #         "discount": promo_reward.discount,
    #         "discount_applicability": promo_reward.discount_applicability,
    #         "program": promo_reward.program,
    #         "discount_line_product": promo_reward.discount_line_product.odoo_id if promo_reward.discount_line_product else None,
    #         "discount_product_ids": promo_reward.discount_product_ids.all(),
    #         "discount_product_category_id": promo_reward.discount_product_category_id.odoo_id if promo_reward.discount_product_category_id else None,
    #         "discount_max_amount": promo_reward.discount_max_amount,
    #         "description": promo_reward.description,
    #         "active": promo_reward.active,
    #         "is_updated": False,
    #         "send_odoo": True,
    #     }
    #     return data, "promo_reward"

    # @staticmethod
    # def prepare_promo_code_data(promo_code):
    #     data = {
    #         "e_id": promo_code.odoo_id or None,
    #         "code": promo_code.code,
    #         "expiration_date": promo_code.expiration_date,
    #         "active": promo_code.active,
    #         "points": promo_code.points,
    #         "program_id": promo_code.program.odoo_id if promo_code.program else None,
    #         "partner_id": promo_code.partner.odoo_id if promo_code.partner else None,
    #         "is_updated": False,
    #         "send_odoo": True,
    #     }
    #     return data, "promo_code"
    
    # @staticmethod
    # def prepare_loyalty_rule_data(rule):
    #     data = {
    #         "e_id": rule.odoo_id or None,
    #         "name": rule.name,
    #         "min_quantity": rule.min_quantity,
    #         "min_amount": rule.min_amount,
    #         "program_id": rule.program.odoo_id if rule.program else None,
    #         "product_id": rule.product.odoo_id if rule.product else None,
    #         "category_id": rule.category.odoo_id if rule.category else None,
    #         "cumulative": rule.cumulative,
    #         "active": rule.active,
    #         "is_updated": False,
    #         "send_odoo": True,
    #     }
    #     return data, "loyalty_rule"