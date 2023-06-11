"""
Managers for payment app
"""

from django.db import models
from django.utils import timezone

# class TransactionQuerySet(models.QuerySet):
#     def authors(self):
#         return self.filter(role='A')

#     def editors(self):
#         return self.filter(role='E')


class TransactionManager(models.Manager):
    # def get_queryset(self):
    #     return PersonQuerySet(self.model, using=self._db)

    # def authors(self):
    #     return self.get_queryset().authors()

    # def editors(self):
    #     return self.get_queryset().editors()


    def create_success(self, order, reference):
        """
        Create transaction object for successfull transaction
        """
        tx = self.create(
            amount=order.price,
            status='success',
            reference=reference,
            paidAt=timezone.now()
        )

        return tx
