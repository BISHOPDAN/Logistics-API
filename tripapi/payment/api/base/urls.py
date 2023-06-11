from django.urls import include, path
from utils.base.routers import CustomDefaultRouter, CustomRouterNoLookup

from . import views

router = CustomRouterNoLookup()
router.register(
    r'bank-account',
    views.BankAccountViewSet,
    basename='bank_account'
)

c_router = CustomDefaultRouter()
c_router.register(
    r'raw-payment',
    views.PaymentViewSet,
    basename='raw_payments'
)

app_name = 'payment'
urlpatterns = [
    path('', include(router.urls)),
    path('', include(c_router.urls)),
    path(
        'authorization-codes/',
        views.SavedUserAuthorizationList.as_view(),
        name='authorization_codes'
    ),
    path(
        'create-payment/<str:tracking_code>/',
        views.CreateTransaction.as_view(),
        name='make_payment'
    ),
    path(
        'callback-payment/',
        views.CallbackTransaction.as_view(),
        name='callback_payment_client'
    ),
]
