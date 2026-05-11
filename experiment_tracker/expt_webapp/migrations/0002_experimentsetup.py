from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('expt_webapp', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExperimentSetup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notes', models.TextField(blank=True, null=True)),
                ('experiment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='experiment_setups', to='expt_webapp.experiment')),
                ('setup', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='experiment_setups', to='expt_webapp.setup')),
            ],
            options={
                'unique_together': {('experiment', 'setup')},
            },
        ),
    ]
