from uuid import uuid4

from account.api.base.permissions import AuthUserIsPartner
from cargo.models import Order
from django.contrib.sites.shortcuts import get_current_site
from django.db.models.query import QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from payment.models import BankAccount, Transaction, UserAuthorizationCode
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from utils.base.flutterwave import payment_client
from utils.base.logger import err_logger, logger  # noqa
from utils.base.mixins import ListMixinUtils, UpdateRetrieveViewSet

from utils.base.general import url_with_params

from . import serializers


class SavedUserAuthorizationList(generics.ListAPIView):
    serializer_class = serializers.UASerializer
    permission_classes = (AuthUserIsPartner,)

    # Filter the queryset to only authorizations for this user
    def get_queryset(self):
        return UserAuthorizationCode.objects.filter(
            user__id=self.request.user.id
        ).order_by('account_name')


# TODO: Review empty permission classes here
class CreateTransaction(generics.GenericAPIView):
    """
    Create new transaction for a connector (order or booking)
    """
    lookup_field = 'tracking_code'
    serializer_class = serializers.CreateTxSerializer

    def get_order(self):
        """
        Get the order to create transaction for
        from the Orders owned by logged in user
        """
        try:
            orders = Order.objects.filter(
                package__user__id=self.request.user.id
            )
            order = orders.get(
                tracking_code=self.kwargs.get(self.lookup_field)
            )
        except Order.DoesNotExist:
            raise Http404('Order with tracking code does not exist')

        return order

    @swagger_auto_schema(
        responses={200: serializers.CreateTxResponse}
    )
    def post(self, request, format=None, *args, **kwargs):
        # Create the callback api url
        site = get_current_site(request).domain
        link = str(reverse('payment:callback_payment_client'))
        callback_api_url = f'{self.request.scheme}://' + site + link

        order = self.get_order()
        reference = uuid4().hex
        link = payment_client.create_init_transaction(
            email=order.package.user.email,
            amount=order.price,
            callback_url=callback_api_url,
            reference=reference
        )
        if link is None:
            message = 'Unable to complete payment, try again.'
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={'message': message}
            )

        callback = request.data.get('callback')
        transaction = Transaction.objects.create(
            amount=order.price,
            status='pending',
            reference=reference,
            redirect_url=callback,
            order=order
        )

        tx_serializer = serializers.TransactionSerializer(transaction)
        data = {
            'authorization_url': link,
            'transaction': tx_serializer.data
        }
        return Response(data=data)


class CallbackTransaction(APIView):
    """
    Process the callback from payment gateway,
    and update the transaction status
    """
    permission_classes = []

    def redirect_response(self, tx_obj: Transaction, params: dict[str, str]):
        redirect_url = tx_obj.redirect_url
        if not redirect_url:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=params)
        redirect_url = url_with_params(redirect_url, params)
        return redirect(redirect_url)

    def get(self, request, *args, **kwargs):
        params = {
            "message": "",
            "status": "error",
        }

        status = request.GET.get('status')
        reference = request.GET.get('tx_ref')
        transaction_id = request.GET.get('transaction_id')

        trans_obj = get_object_or_404(Transaction, reference=reference)
        params["tracking_code"] = trans_obj.get_tx_tracking_code()

        # Check the transaction verification status on paystack
        status = payment_client\
            .verify_transaction(
                transaction_id,
                trans_obj.amount
            )

        if status is None:
            params['message'] = 'Unable to verify transaction'
            return self.redirect_response(trans_obj, params)

        if status:
            trans_obj.status = 'success'
            trans_obj.paidAt = timezone.now()
        else:
            trans_obj.status = 'failed'
        trans_obj.save()

        if status:
            trans_obj.update_success()

        return self.redirect_response(trans_obj, params)


class BankAccountViewSet(UpdateRetrieveViewSet):
    """
    Views for update and retrieving user account details
    """
    serializer_class = serializers.BankAccountSerializer
    permission_classes = (AuthUserIsPartner,)

    def get_queryset(self):
        return BankAccount.objects.all()

    def get_object(self):
        return self.request.user.bankaccount


class PaymentViewSet(ListMixinUtils, viewsets.ReadOnlyModelViewSet):
    """
    Views for listing and retrieving payments
    """
    serializer_class = serializers.PaymentSerializer
    permission_classes = (AuthUserIsPartner,)
    lookup_field = 'tracking_code'

    def get_queryset(self):
        return Transaction.objects.filter(
            bank_account=self.request.user.bankaccount)

    def get_transaction_filter(self, status: str) -> QuerySet:
        """Filter partner transactions by their status"""
        return self.filter_queryset(
            self.get_queryset()).filter(status=status)

    @action(detail=False, methods=['get'], url_path='status/pending')
    def pending_payments(self, request, *args, **kwargs):
        """Get all pending payments for partner"""
        queryset = self.get_transaction_filter('pending')
        return self.get_with_queryset(queryset)

    @action(detail=False, methods=['get'], url_path='status/success')
    def successful_payments(self, request, *args, **kwargs):
        """Get all success payments for partner"""
        queryset = self.get_transaction_filter('success')
        return self.get_with_queryset(queryset)

    @action(detail=False, methods=['get'], url_path='status/failed')
    def failed_payments(self, request, *args, **kwargs):
        """Get all failed payments for partner"""
        queryset = self.get_transaction_filter('failed')
        return self.get_with_queryset(queryset)
