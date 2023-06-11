from django.contrib import admin

from .models import Driver, Logistic, Order, Package, PricePackage, Review


class PricePackageInline(admin.TabularInline):
    model = PricePackage


@admin.register(Logistic)
class LogisticAdmin(admin.ModelAdmin):
    list_display = ('name', 'rating',)
    search_fields = ('name',)
    inlines = (PricePackageInline,)


@admin.register(PricePackage)
class PricePackageAdmin(admin.ModelAdmin):
    list_display = ('logistic', 'from_location',
                    'to_location', 'price', 'tracking_code',)
    search_fields = ('from_location', 'to_location', 'tracking_code',)


admin.site.register([Package, Order, Review, Driver])
