"""
Payment models for payment system
"""

from django.db import models

from .managers import TransactionManager

from utils.base.mixins import CreatedMixin, ModelChangeFunc
from utils.base.fields import TrackingCodeField


class BankAccount(models.Model):
    bank = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    account_name = models.CharField(max_length=50, blank=True, null=True)
    user = models.OneToOneField(
        'account.User', on_delete=models.CASCADE)
    total_revenue = models.FloatField(default=0.0)

    def stabilize_amount(self, old: int, new: int, commit=True):
        """Stabilize account balance"""
        self.total_revenue -= old
        self.total_revenue += new

        if commit:
            self.save()

    def __str__(self) -> str:
        return self.user.profile.get_fullname


class Transaction(CreatedMixin, ModelChangeFunc):
    """
    Transaction for payments
    """
    tracking_code = TrackingCodeField(prefix="TRX-RPT", max_length=60)

    objects = TransactionManager()

    STATUS = (
        ('pending', "Pending"),
        ('success', "Success"),
        ('failed', "Failed"),
    )

    amount = models.FloatField(default=0.0)
    paidAt = models.DateTimeField(null=True, editable=False)
    status = models.CharField(choices=STATUS, max_length=10)
    reference = models.CharField(max_length=300, unique=True)
    redirect_url = models.URLField(blank=True)

    name = models.CharField(
        max_length=50, help_text='Name of person making payment')
    bank_account: BankAccount = models.OneToOneField(
        BankAccount, on_delete=models.CASCADE, null=True)
    order = models.OneToOneField(
        'cargo.Order', on_delete=models.CASCADE, null=True)
    booking = models.OneToOneField(
        'transport.Booking', on_delete=models.CASCADE, null=True)

    def is_order(self) -> bool:
        """Return if the transaction is connected to a Package order"""
        return self.order is not None

    def is_booking(self) -> bool:
        """Return if the transaction is connected to a Trip booking"""
        return self.booking is not None

    def get_tx_type_obj(self):
        """Get the transaction object"""
        if self.is_order():
            return self.order
        elif self.is_booking():
            return self.booking

    def get_tx_tracking_code(self):
        """Get the tracking code for the
        transaction and attached connector"""
        return self.get_tx_type_obj().get_tx_tracking_code()

    def update_success(self):
        """Call success of the transaction connector"""
        return self.get_tx_type_obj().update_success()

    def update_total_revenue(self):
        """Make sure total_revenue of user account is accurate"""
        if self.status == 'success' and self.bank_account is not None:
            old_amount = self.get_attr(self.get_clone_field('amount')) or 0
            self.bank_account.stabilize_amount(old_amount, self.amount)

    monitor_change = {
        'amount': update_total_revenue,
        'status': update_total_revenue,
    }

    def __str__(self) -> str:
        return self.reference


class UserAuthorizationCode(models.Model):
    """
    Save paystack authorization code for reuse
    """
    user = models.ForeignKey('account.User', on_delete=models.CASCADE)
    authorization_code = models.CharField(max_length=50)
    signature = models.CharField(max_length=70, unique=True)

    email = models.EmailField()
    account_name = models.CharField(max_length=100, blank=True)
    country_code = models.CharField(max_length=100, blank=True)
    channel = models.CharField(max_length=100, blank=True)
    reusable = models.BooleanField()

    # Card details
    brand = models.CharField(max_length=100, blank=True)
    last4 = models.CharField(max_length=4, blank=True)
    exp_month = models.CharField(max_length=2, blank=True)
    exp_year = models.CharField(max_length=4, blank=True)
    bin = models.CharField(max_length=6, blank=True)
    bank = models.CharField(max_length=60, blank=True)

    def get_display_detail(self):
        return f"{self.brand.capitalize()} *********{self.last4}"

    def __str__(self) -> str:
        return self.email
