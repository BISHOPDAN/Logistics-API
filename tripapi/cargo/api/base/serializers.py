from rest_framework import serializers

from cargo.models import Driver, Package, Order, Logistic, PricePackage

from payment.api.base.serializers import TransactionSerializer
from transport.api.base import serializers as t_serializers


class CargoTypeSerializer(serializers.Serializer):
    key = serializers.CharField(help_text='This is a key of the choices')
    value = serializers.CharField(help_text='This is a value of the choices')


class ManyCargoTypeSerializer(serializers.Serializer):
    choice = CargoTypeSerializer(many=True)


class LogisticSerializer(serializers.ModelSerializer):
    class Meta:
        model = Logistic
        exclude = ('user', 'id',)


class LogisticCreateImageSerializer(serializers.ModelSerializer):

    class Meta:
        model = Logistic
        fields = ('logistics_image',)


class CreateOrderFromPricePackageSerializer(serializers.Serializer):
    package_code = serializers.CharField(max_length=20)
    price_code = serializers.CharField(max_length=20)


class SearchPackageByTrackingCodeSerializer(serializers.Serializer):
    tracking_code = serializers.CharField(max_length=20)


class PricePackageSerializerNoTotalField(serializers.ModelSerializer):
    logistic = LogisticSerializer(read_only=True)

    class Meta:
        model = PricePackage
        exclude = ('id',)


class PricePackageSerializer(PricePackageSerializerNoTotalField):
    total_price = serializers.SerializerMethodField()

    def get_total_price(self, obj):
        package = self.context.get('package')
        return obj.price * 2 * package.weight * package.quantity


class OrderSerializer(serializers.ModelSerializer):
    transaction = TransactionSerializer(read_only=True)
    logistic_package = PricePackageSerializerNoTotalField(read_only=True)
    readable_status = serializers.CharField()

    class Meta:
        model = Order
        exclude = ('id',)
        read_only_fields = ('user', 'transaction',
                            'package', 'readable_status',)


class PricePackageRouteSerializer(serializers.ModelSerializer):

    class Meta:
        model = PricePackage
        exclude = ('id', 'logistic')


class PackageSerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True)
    get_cargo_type = serializers.CharField(read_only=True)

    class Meta:
        model = Package
        exclude = ('user', 'id', 'price_packages',)
        read_only_fields = ('order', 'tracking_code',)


class PackageSerializerWithoutOrder(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = ('pickup', 'delivery', 'tracking_code')
        read_only_fields = ('tracking_code',)


class DriverSerializer(
    t_serializers.DriverSerializer
):
    packages_assigned = serializers.SerializerMethodField()
    trips_added = None

    class Meta:
        model = Driver
        ref_name = 'LogisticDriverSerializer'
        exclude = ('user', 'active', 'logistic')

    def get_packages_assigned(self, obj):
        return obj.get_packages_assigned()


class AssignDriverOrderSerializer(serializers.Serializer):
    driver_id = serializers.IntegerField()
    order_id = serializers.IntegerField()

    def validate_order_id(self, value):
        logistic_id = self.context.get('logistic_id')
        order = Order.objects.filter(
            id=value, logistic_package__logistic__id=logistic_id).first()
        if not order:
            raise serializers.ValidationError('Order does not exist')
        self.context['order'] = order
        return value

    def validate_driver_id(self, value):
        logistic_id = self.context.get('logistic_id')
        driver = Driver.objects.filter(
            id=value, logistic__id=logistic_id).first()
        if not driver:
            raise serializers.ValidationError('Driver does not exist')
        self.context['driver'] = driver
        return value

    def save(self, **kwargs):
        order = self.context.get('order')
        driver = self.context.get('driver')
        order.driver = driver
        order.save()
        return order
