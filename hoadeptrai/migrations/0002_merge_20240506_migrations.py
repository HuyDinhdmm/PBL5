from django.db import migrations, models
import django.utils.timezone

class Migration(migrations.Migration):

    dependencies = [
        ('hoadeptrai', '0001_initial'),
    ]

    operations = [
        # Add promotion timestamps
        migrations.AddField(
            model_name='promotion',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='promotion',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='promotion',
            name='usage_count',
            field=models.IntegerField(default=0),
        ),
        
        # Add order payment fields
        migrations.AddField(
            model_name='order',
            name='payment_status',
            field=models.CharField(
                choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')],
                default='pending',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='zalopay_trans_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='payment_method',
            field=models.CharField(
                blank=True,
                choices=[('cod', 'Cash on Delivery'), ('zalopay', 'ZaloPay')],
                max_length=20,
                null=True
            ),
        ),
    ]
