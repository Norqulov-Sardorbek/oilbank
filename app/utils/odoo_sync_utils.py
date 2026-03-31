import json
import os
import logging

import requests
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from importlib import import_module

from app.models.log_connection import OdooConnectorLogger
from app.utils.utils import OdooSync

logger = logging.getLogger(__name__)


def get_model_class(model_class_path):
    """Dinamik ravishda model klassini olish"""
    try:
        module_path, class_name = model_class_path.rsplit(".", 1)
        module = import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError, ValueError) as e:
        logger.error(f"Model klassini olishda xato: {model_class_path} - {str(e)}")
        raise


def execute_odoo_operation(
    operation_type, model_name, instance_id, model_class_path, **kwargs
):
    try:
        ModelClass = get_model_class(model_class_path)
        instance = ModelClass.objects.get(pk=instance_id)

        logger_manager = OdooConnectorLogger(
            operation_type=operation_type,
            model_name=model_name,
            local_model=ModelClass.__name__,
            instance_id=instance_id,
            odoo_id=getattr(instance, kwargs.get("odoo_id_field", "odoo_id"), None),
        )

        logger.info(f"model name: {ModelClass}")
        logger.info(f"Instance odoo id: {instance.odoo_id}")

        with logger_manager.log_operation():
            odoo_sync = OdooSync()
            if operation_type == "create":
                result = odoo_sync.create_to_odoo(model_name, instance)
            elif operation_type == "update":
                result = odoo_sync.send_to_odoo(
                    model_name, instance, kwargs.get("odoo_id_field", "odoo_id")
                )
            elif operation_type == "delete":
                result = odoo_sync.send_to_odoo_delete(
                    model_name, instance, kwargs.get("odoo_id_field", "odoo_id")
                )

            return result

    except ObjectDoesNotExist:
        if operation_type == "delete":
            e_id = kwargs.get("e_id")
            if e_id:
                logger_manager = OdooConnectorLogger(
                    operation_type="delete",
                    model_name=model_name,
                    local_model=model_class_path.split(".")[-1],
                    instance_id=None,
                    odoo_id=e_id,
                )

                with logger_manager.log_operation():
                    try:
                        payload = {"model": model_name, "e_id": e_id}
                        logger_manager.update_response({"request_payload": payload})

                        response = requests.post(
                            url=f"{settings.ODOO_API_URL}/api/delete/django_to_odoo",
                            data=json.dumps(payload),
                            headers={"Content-Type": "application/json"},
                            timeout=10,
                        )
                        response.raise_for_status()

                        logger_manager.update_response(response.json())
                        return True
                    except Exception as e:
                        logger_manager.update_response({"error": str(e)})
                        raise
        logger.info(f"Model {model_name} id={instance_id} mavjud emas")
        logger.info(f"Odoo excetionda chiqdi error")
        return False
    except Exception as e:
        logger.error(f"Odoo {operation_type} xatosi: {model_name} id={instance_id}")
        raise
