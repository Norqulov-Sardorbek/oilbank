from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0182_videocategory_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='qrcode',
            name='serial_number',
            field=models.PositiveIntegerField(blank=True, null=True, unique=True),
        ),
        migrations.AlterModelOptions(
            name='qrcode',
            options={'ordering': ['serial_number']},
        ),
    ]
