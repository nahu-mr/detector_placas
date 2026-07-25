# Generated manually for PlateMind vehicle and owner details

from django.db import migrations, models


def copiar_propietario(apps, schema_editor):
    Registrada = apps.get_model('control', 'Registrada')
    for registro in Registrada.objects.all():
        if not registro.nombre_propietario or registro.nombre_propietario == 'Sin especificar':
            registro.nombre_propietario = registro.propietario or 'Sin especificar'
            registro.save(update_fields=['nombre_propietario'])


class Migration(migrations.Migration):

    dependencies = [
        ('control', '0008_alter_entrada_entrada'),
    ]

    operations = [
        migrations.AddField(
            model_name='registrada',
            name='nombre_propietario',
            field=models.CharField(default='Sin especificar', max_length=100),
        ),
        migrations.AddField(
            model_name='registrada',
            name='dni_propietario',
            field=models.CharField(blank=True, default='', max_length=12),
        ),
        migrations.AddField(
            model_name='registrada',
            name='modelo_auto',
            field=models.CharField(blank=True, default='', max_length=80),
        ),
        migrations.AddField(
            model_name='registrada',
            name='color_auto',
            field=models.CharField(blank=True, default='', max_length=40),
        ),
        migrations.RunPython(copiar_propietario, migrations.RunPython.noop),
    ]
