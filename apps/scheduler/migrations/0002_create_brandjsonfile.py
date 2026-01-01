# Auto-generated migration to create BrandJsonFile when initial was faked but table missing
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BrandJsonFile',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now, editable=False)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('filename', models.CharField(blank=True, max_length=1024, null=True)),
                ('file_path', models.CharField(blank=True, max_length=2048, null=True)),
                ('last_synced', models.DateTimeField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('is_deleted', models.BooleanField(default=False, db_index=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_%(class)s_set', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_%(class)s_set', to=settings.AUTH_USER_MODEL)),
                ('brand', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='json_files', to='brand.brand')),
                ('template', models.CharField(max_length=255)),
            ],
            options={
                'db_table': 'brand_json_file',
                'unique_together': {('brand', 'template')},
            },
        ),
    ]
