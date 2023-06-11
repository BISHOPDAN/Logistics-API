from django.urls import path
# from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'auth'
urlpatterns = [
    path('register/', views.RegisterAPIView.as_view(), name='register'),
    path('login/', views.LoginAPIView.as_view(), name='login'),
    path('forget-password/<str:email>/',
         views.ForgetPasswordView.as_view(), name='forget_password'),

    # Tokens
    path('token/user/refresh/',
         views.TokenRefreshAPIView.as_view(), name='token_refresh'),
    path('token/user/validate/',
         views.TokenVerifyAPIView.as_view(), name='token_validate'),

    # Path for changing user password
    path('user/forgetPassword/', views.ForgetChangePasswordView.as_view(),
         name='forget_password_change'),
    path('user/changePassword/', views.ChangePasswordView.as_view(),
         name='change_password'),
    path('user/profile/update/',
         views.ProfileAPIView.as_view(), name='detail_profile'),

    # Get user verify token for email verification
    path('token/email/generate/',
         views.GenerateTokenView.as_view(), name='gen_token'),
    path('token/email/validate/',
         views.ValidateTokenView.as_view(), name='validate_token'),

    # Paths for getting and finding user informations
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/detail/', views.UserAPIView.as_view(), name='user_data'),

    # Extra utility paths
    path('utils/send-mail/', views.SendMailView.as_view(), name='send_mail'),
    path('utils/generate/', views.GenerateTokenViewForEmail.as_view(),
         name='unique_gen_token'),
    path('utils/generate_otp/', views.GenerateOtpView.as_view(),
         name='gen_otp'),
    path('utils/add-newsletter/',
         views.NewsletterAPICreate.as_view(), name='newsletter_add'),

]
