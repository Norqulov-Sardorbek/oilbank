from rest_framework import serializers
from datetime import time
from app.models.company_info import Branch
from app.models.booking import Appointment, AppointmentWorkingDay, Resource
from rest_framework.response import Response
from rest_framework import status


class ResourceSerializer(serializers.ModelSerializer):
    sync_status = serializers.ChoiceField(
        choices=["created", "updated", "deleted", "synced"],
        default="created",
        read_only=True,
    )

    class Meta:
        model = Resource
        fields = [
            "odoo_id",
            "name",
            "description",
            "sync_status",
        ]
        read_only_fields = ["sync_status"]

    def create(self, validated_data):
        resource = Resource.objects.create(**validated_data)
        return resource

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class AppointmentSerializer(serializers.ModelSerializer):
    branch_odoo_id = serializers.CharField(write_only=True, required=False)
    sync_status = serializers.ChoiceField(
        choices=["created", "updated", "deleted", "synced"],
        default="created",
        read_only=True,
    )
    resource_odoo_ids = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )

    class Meta:
        model = Appointment
        fields = [
            "odoo_id",
            "name",
            "duration",
            "branch_odoo_id",
            "sync_status",
            "resource_odoo_ids",
        ]
        read_only_fields = ["sync_status"]

    def validate_branch_odoo_id(self, value):
        try:
            branch = Branch.objects.get(odoo_id=value)
        except Branch.DoesNotExist:
            raise serializers.ValidationError(
                f"Branch with odoo_id {value} does not exist."
            )
        return value

    def validate_resource_odoo_ids(self, value):
        if not value:
            return value
        resources = Resource.objects.filter(odoo_id__in=value)
        found_odoo_ids = set(resource.odoo_id for resource in resources)
        missing_ids = set(value) - found_odoo_ids
        if missing_ids:
            raise serializers.ValidationError(
                f"Resources with odoo_ids {missing_ids} do not exist."
            )
        return value

    def validate(self, data):
        if "duration" in data:
            try:
                duration_hours = float(data["duration"])
                if duration_hours < 0:
                    raise ValueError
                data["duration"] = int(duration_hours * 60)
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    "Duration must be a valid number in hours (e.g., 1.0 for 1 hour)."
                )
        return data

    def create(self, validated_data):
        branch_odoo_id = validated_data.pop("branch_odoo_id")
        resource_odoo_ids = validated_data.pop("resource_odoo_ids", [])
        branch = Branch.objects.get(odoo_id=branch_odoo_id)
        appointment = Appointment.objects.create(branch=branch, **validated_data)
        if resource_odoo_ids:
            resources = Resource.objects.filter(odoo_id__in=resource_odoo_ids)
            appointment.resources.set(resources)
        return appointment

    def update(self, instance, validated_data):
        branch_odoo_id = validated_data.pop("branch_odoo_id", None)
        resource_odoo_ids = validated_data.pop("resource_odoo_ids", None)
        if branch_odoo_id:
            branch = Branch.objects.get(odoo_id=branch_odoo_id)
            instance.branch = branch
        if resource_odoo_ids is not None:
            resources = Resource.objects.filter(odoo_id__in=resource_odoo_ids)
            instance.resources.set(resources)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class OdooDayField(serializers.ChoiceField):

    def to_internal_value(self, data):
        try:
            v = int(data)
        except (TypeError, ValueError):
            self.fail("invalid_choice", input=data)

        if 1 <= v <= 7:
            v = v - 1
        else:
            self.fail("invalid_choice", input=data)

        return super().to_internal_value(v)


class AppointmentWorkingDaySerializer(serializers.ModelSerializer):
    day = OdooDayField(choices=Appointment.DAY_CHOICES)
    appointment_odoo_id = serializers.CharField(write_only=True, allow_null=True)
    sync_status = serializers.ChoiceField(
        choices=["created", "updated", "deleted", "synced"],
        default="created",
        read_only=True,
    )

    class Meta:
        model = AppointmentWorkingDay
        fields = [
            "odoo_id",
            "appointment_odoo_id",
            "day",
            "opening_time",
            "closing_time",
            "sync_status",
        ]
        read_only_fields = ["sync_status"]

    def validate_appointment_odoo_id(self, value):
        if value:
            try:
                Appointment.objects.get(odoo_id=value)
            except Appointment.DoesNotExist:
                raise serializers.ValidationError(
                    f"Appointment with odoo_id {value} does not exist."
                )
        return value

    def validate(self, data):
        for field in ["opening_time", "closing_time"]:
            if field in data and isinstance(data[field], float):
                hours = int(data[field])
                minutes = int(round((data[field] - hours) * 60))
                data[field] = time(hours, minutes)
        return data

    def create(self, validated_data):
        appointment_odoo_id = validated_data.pop("appointment_odoo_id", None)
        appointment = None
        if appointment_odoo_id:
            appointment = Appointment.objects.get(odoo_id=appointment_odoo_id)
        return AppointmentWorkingDay.objects.create(
            appointment=appointment, **validated_data
        )

    def update(self, instance, validated_data):
        appointment_odoo_id = validated_data.pop("appointment_odoo_id", None)
        if appointment_odoo_id:
            instance.appointment = Appointment.objects.get(odoo_id=appointment_odoo_id)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance