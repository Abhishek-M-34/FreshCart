from django.db import migrations, models
import uuid
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="building",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="order",
            name="checkout_key",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="order",
            name="city",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="order",
            name="district",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="order",
            name="latitude",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="longitude",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_method",
            field=models.CharField(choices=[("COD", "Cash on Delivery"), ("ONLINE", "Online Payment")], default="COD", max_length=20),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_status",
            field=models.CharField(choices=[("PENDING", "Pending"), ("PAID_DEMO", "Paid (Demo)")], default="PENDING", max_length=20),
        ),
        migrations.AddField(
            model_name="order",
            name="phone",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="order",
            name="pin_code",
            field=models.CharField(blank=True, max_length=6),
        ),
        migrations.AddField(
            model_name="order",
            name="recipient_name",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="order",
            name="state",
            field=models.CharField(blank=True, default="Kerala", max_length=100),
        ),
        migrations.AddField(
            model_name="order",
            name="street",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="order",
            name="transaction_id",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.CreateModel(
            name="DemoPaymentSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session_key", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("checkout_key", models.CharField(max_length=64, unique=True)),
                ("payload", models.JSONField()),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("status", models.CharField(choices=[("waiting", "Waiting"), ("success", "Success")], default="waiting", max_length=20)),
                ("transaction_id", models.CharField(blank=True, max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("order", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="demo_payment_session", to="orders.order")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="demo_payment_sessions", to="auth.user")),
            ],
        ),
    ]
