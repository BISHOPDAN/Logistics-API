import shutil
from pathlib import PurePath

from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify
from utils.base.fields import TrackingCodeField
from utils.base.logger import err_logger, logger  # noqa
from utils.base.logistics.image import driver_id_path, driver_licence_path, logistics_unique_filename
from utils.base.validators import (validate_phone, validate_rating_level,
                                   validate_special_char)

from .managers import PricePackageManager


class Logistic(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    name = models.CharField(
        max_length=100, validators=[validate_special_char], unique=True)

    slug_name = models.SlugField(blank=True, max_length=200, unique=True)
    rating = models.FloatField(default=0.0)
    logistics_image = models.ImageField(
        upload_to=logistics_unique_filename, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Create slug name
        if not self.id:
            self.slug_name = slugify(self.name)

        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Driver(models.Model):
    """
    Logistic's drivers model
    """
    tracking_code = TrackingCodeField(prefix="LOG_DVR")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='logistic_driver'
    )
    logistic = models.ForeignKey(Logistic, on_delete=models.CASCADE)
    verified = models.BooleanField(default=False)
    licence = models.ImageField(
        upload_to=driver_licence_path, null=True, blank=True)
    id_card = models.ImageField(
        upload_to=driver_id_path, null=True, blank=True)
    active = models.BooleanField(default=False)
    send_mail_verification = models.BooleanField(default=False)

    def get_packages_assigned(self) -> int:
        """
        Get number of packages driver
        is assigned to deliver
        """
        return self.order_set.all().count()

    def __str__(self):
        return self.user.profile.fullname


class PricePackage(models.Model):
    """This is also known as Route Plan

    :param models: _description_
    :type models: _type_
    """
    tracking_code = TrackingCodeField(prefix="LGS-PRC", max_length=60)
    logistic = models.ForeignKey(Logistic, on_delete=models.CASCADE)
    from_location = models.CharField(
        help_text='Location where goods will shipped from', max_length=255)
    to_location = models.CharField(
        help_text='Location where goods will shipped to', max_length=255)
    price = models.FloatField(
        help_text='Price per 0.5kg for the goods to be shipped')

    pickup_time = models.IntegerField(
        help_text='''Amount of days to pickup from payment day.
        e.g if you input 2, that means you will pickup on the
        second day after payment day.''',
        default=0)
    delivery_date = models.IntegerField(
        default=2, help_text='The amount of days after pickup to delivery')

    active = models.BooleanField(default=True)

    objects = PricePackageManager()

    class Meta:
        verbose_name = 'Package Shipping Price'
        ordering = ('-price',)


class Package(models.Model):
    """
    Package to be ordered created by users
    """
    CARGO_TYPE = (
        ('parcel', 'Parcel',),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)

    # Sender's info
    name = models.CharField(max_length=40, validators=[validate_special_char])
    phone = models.CharField(max_length=17, validators=[validate_phone])
    email = models.EmailField()

    # Receiver's info
    receiver_name = models.CharField(
        max_length=40, validators=[validate_special_char])

    receiver_phone = models.CharField(
        max_length=17, validators=[validate_phone])

    receiver_email = models.EmailField()

    # Cargo details
    cargo = models.CharField(choices=CARGO_TYPE, max_length=20)
    cargo_name = models.CharField(max_length=100)
    quantity = models.FloatField(default=0.0)
    weight = models.FloatField(default=0.0)
    pickup = models.CharField(max_length=200)
    delivery = models.CharField(max_length=200)

    created = models.DateTimeField(auto_now_add=True)

    # Price packages for saving logistics packages
    # available to package to select
    price_packages = models.ManyToManyField(PricePackage)

    tracking_code = TrackingCodeField(prefix="PKG", max_length=60)

    @property
    def get_cargo_type(self):
        return self.get_cargo_display()

    def __str__(self):
        return self.cargo_name


class Order(models.Model):
    """
    Order database model for packages ordered by users
    """
    DELIVERY_STATUS = (
        ('unpicked', 'Unpicked',),
        ('pickup', 'Pickup',),
        ('in_warehouse', 'In warehouse',),
        ('in_transit', 'In transit',),
        ('delivered', 'Delivered',),
        ('cancelled', 'Cancelled',),
    )
    package = models.OneToOneField(Package, on_delete=models.CASCADE)
    logistic_package = models.ForeignKey(
        PricePackage, on_delete=models.PROTECT)
    price = models.FloatField()
    status = models.CharField(
        choices=DELIVERY_STATUS, max_length=25, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    pickup_date = models.DateField(null=True, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    tracking_code = TrackingCodeField(prefix="LGP-ORD", max_length=60)
    driver = models.ForeignKey(
        Driver, on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def readable_status(self):
        return self.get_status_display()

    def get_tx_tracking_code(self) -> str:
        """Get the transaction tracking code"""
        return self.package.tracking_code

    def get_transaction(self):
        """
        Get the transaction for the order
        """
        if not self.transaction:
            raise ValueError('Transaction not found')
        return self.transaction

    def update_success(self):
        """
        Process order after successful payment
        """
        transaction = self.get_transaction()
        paid_at = transaction.paidAt

        # Update pickup date
        pickup_time = self.logistic_package.pickup_time
        amount_of_days = timezone.timedelta(days=pickup_time)
        self.pickup_date = paid_at + amount_of_days

        # Update delivery date
        amount_of_days = timezone.timedelta(
            days=self.logistic_package.delivery_date + pickup_time)

        self.delivery_date = paid_at + amount_of_days

        # Update package status
        self.status = 'unpicked'

        self.save()

    def __str__(self):
        return self.package.__str__()


class Review(models.Model):
    """
    Reveiw for Logistics
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    rating = models.IntegerField(default=0, validators=[validate_rating_level])
    comment = models.TextField()

    def __str__(self):
        return self.order.__str__()

    class Meta:
        verbose_name = 'Logistic review'


@receiver(post_delete, sender=Driver)
def delete_driver_user(sender, instance, **kwargs):
    """Delete the driver user and driver images"""
    instance.user.delete()

    dir_path = None
    if instance.licence:
        dir_parts = PurePath(instance.licence.path).parts[:-2]
        dir_path = PurePath('').joinpath(*dir_parts)
    elif instance.id_card:
        dir_parts = PurePath(instance.id_card.path).parts[:-2]
        dir_path = PurePath('').joinpath(*dir_parts)

    if dir_path is not None:
        shutil.rmtree(dir_path, ignore_errors=True)
