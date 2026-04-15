
from rest_framework import serializers
from app.models.help_services import HelpService, HelpServiceEmployee



class HelpServiceEmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpServiceEmployee
        fields = ['id', 'name', 'icon', 'phone']
        read_only_fields = ['id']


class HelpServiceSerializer(serializers.ModelSerializer):
    employees = HelpServiceEmployeeSerializer(many=True, read_only=True)

    class Meta:
        model = HelpService
        fields = ['id', 'name_uz', 'name_ru', 'name_en', 'description', 'description_ru', 'description_en', 'icon',  'employees']
        read_only_fields = ['id']