from rest_framework import serializers
from app.models.help_services import HelpService, HelpServiceEmployee



class HelpServiceEmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpServiceEmployee
        fields = ['id', 'name', 'icon', 'phone']
        read_only_fields = ['id']


class HelpServiceSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()


    class Meta:
        model = HelpService
        fields = ['id', 'name', 'description', 'icon']
        read_only_fields = ['id']

    def get_lang(self):
        lang = self.context.get("accept_language", "uz")
        return lang.split(",")[0].split("-")[0]
    
    def get_name(self, obj):
        lang = self.get_lang()

        if lang == "ru":
            return obj.name_ru or obj.name_uz
        elif lang == "en":
            return obj.name_en or obj.name_uz
        return obj.name_uz

    def get_description(self, obj):
        lang = self.get_lang()

        if lang == "ru":
            return obj.description_ru or obj.description
        elif lang == "en":
            return obj.description_en or obj.description
        return obj.description