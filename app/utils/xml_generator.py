import os
import re
from decimal import Decimal

from django.conf import settings
from django.template.loader import get_template
from django.utils.safestring import mark_safe
from django.utils.translation import get_language
from htmlmin import minify
from django.utils.translation import gettext_lazy as _

class CheckXMLGenerator:
    def __init__(self, template_path='template_check_uz.xml'):
        self.template_path = template_path

    def generate_using_jinja2(self, check, company=None):
        lang = get_language()
        if lang not in ["en", "uz", "ru"]:
            lang = "en"
        
        if lang == "ru":
            self.template_path = 'template_check_ru.xml'
        elif lang == "en":
            self.template_path = 'template_check_en.xml'
        
        template_name = os.path.basename(self.template_path)

        # Get Django template
        template = get_template(template_name)

        # Prepare data
        context_data = self._prepare_context_data(check, company)

        # Render template and minify
        html_content = template.render(context_data)
        return self._clean_html(html_content)

    def _clean_html(self, html_content):
        """
        Clean and minify HTML using htmlmin
        """
        return minify(
            html_content,
            remove_comments=True,
            remove_empty_space=True,
            reduce_boolean_attributes=True,
            remove_optional_attribute_quotes=False,
            keep_pre=True,
            # parse_style=False  
        )
    def _prepare_context_data(self, check, company=None, request=None):
        order = check.order
        user = check.user

        if request:
            base_url = request.build_absolute_uri('/')
            if company and company.image:
                company_logo_url = f"{base_url}{settings.MEDIA_URL}{company.image}"
            else:
                company_logo_url = None
        else:
            company_logo_url = company.image.url if company and company.image else None

        if not company:
            company = order.branch if order and order.branch else None
        
        products_rows = self._generate_products_rows(check)
        cashback_data = self._calculate_cashback_data(check)

        lang = get_language()
        if lang not in ["en", "uz", "ru"]:
            lang = "en"
        name_lang_field = f"name" if lang == "uz" else f"name_{lang}"
        company_name = getattr(company, name_lang_field, company.name) if company else None
        vat = company.vat if company and company.vat else None
        return {
            'company_logo': company_logo_url,
            'company_name': company_name,
            'vat':vat,
            'company_city': company.city if company and hasattr(company, 'city') else None,
            'company_street': company.street if company and hasattr(company, 'street') else None,
            'company_phone': company.phone if company and hasattr(company, 'phone') else None,
            'cashier_name': order.created_by.get_full_name() if order and hasattr(order, 'created_by') else 'Administrator',
            'order_number': _("No order name") if order and order.name == "No order name" else order.name,
            'order_id': str(order.id) if order else '',
            'customer_name': user.get_full_name() if user else 'Customer',
            'order_date': order.created_at.strftime('%d/%m/%Y %H:%M:%S') if order else '',
            'products_rows': mark_safe(products_rows),
            'current_balance': f"{cashback_data['current_balance']:.2f}",
            'cashback_used': f"{abs(check.balance_amount):.2f}" if check.balance_amount > 0 else "0.0",
            'cashback_added': f"{check.given_cashback:.2f}",
            'cashback_percentage': order.balance_percentage,
            'cashback_status_name': order.balance_status_name,
            'total_amount': f"{check.amount:.2f}",
            'card_amount': f"{order.card_amount:.2f}",
            'cash_amount':f"{order.cash_amount:.2f}",
            'source': order.source,
            'payment_method': self._get_payment_method_display(check.payment_type),
            'currency': 'UZS',
            'fm_num': order.fm_num or '',
            'f_num': order.f_num or '',
            'qr_url': order.fiscal_url or '',
        }

    def _generate_products_rows(self, check):
        if not check.order:
            return ''
        
        rows = []
        for item in check.order.items.all():
            if item.product and item.product.product_type not in ["CASHBACK", "DELIVERY_PRICE","COUPON"]:
                rows.append(
                    f"<tr><td>{item.product.name}</td><td>{item.quantity}</td><td>{item.price:.2f}</td><td>{item.total_price:.2f} UZS</td></tr>"
                )
        return ''.join(rows)

    def _calculate_cashback_data(self, check):
        current_balance = Decimal('0.0')
        percentage = check.order.balance_percentage if check.order else 0

        if check.user:
            from app.models.card import Balance
            user_cashback = Balance.objects.filter(user=check.user).first()
            if user_cashback:
                current_balance = user_cashback.balance 

        return {
            'current_balance': current_balance,
            'percentage': percentage
        }

    def _get_payment_method_display(self, payment_type):
        payment_methods = {
            'CASH': 'Naqd',
            'CARD': 'Karta',
            'CLICK': 'Click',
            'PAYME': 'Payme',
            'UZUM': 'Uzum',
        }
        return payment_methods.get(payment_type, payment_type)
