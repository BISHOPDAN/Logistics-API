from django.contrib.postgres.search import (SearchQuery, SearchRank,
                                            SearchVector)
from django.db import models
from django.db.models import Q


class PricePackageQuery(models.QuerySet):
    def find_logistic(self, pickup, delivery):
        """Use details in package to find the best
        and available Price Packages for the job"""

        # Create Vector and Query for ranking
        from_vector = SearchVector('from_location')
        to_vector = SearchVector('to_location')
        from_query = SearchQuery(pickup)
        to_query = SearchQuery(delivery)

        from_ranking = SearchRank(from_vector, from_query)
        to_ranking = SearchRank(to_vector, to_query)

        selected = self.select_related('logistic')\
            .annotate(from_rank=from_ranking)\
            .annotate(to_rank=to_ranking)\
            .filter(Q(from_rank__gte=0.001) & Q(to_rank__gte=0.001))\
            .order_by('-from_rank', '-to_rank')

        return selected


class PricePackageManager(models.Manager):
    def get_queryset(self):
        return PricePackageQuery(model=self.model, using=self._db)

    def find_logistic(self, pickup, delivery):
        return self.get_queryset().find_logistic(pickup, delivery)
