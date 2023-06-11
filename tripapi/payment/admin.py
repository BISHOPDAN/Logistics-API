from django.contrib import admin

# Register your models here.
from .models import BankAccount, Transaction, UserAuthorizationCode


admin.site.register([Transaction, UserAuthorizationCode, BankAccount])
