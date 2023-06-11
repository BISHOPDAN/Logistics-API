from account.api.base.permissions import (AuthUserIsLogistic, BasicPerm,
                                          SuperPerm)
from cargo.models import Driver, Order, Package, PricePackage
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from transport.api.base.serializers import SearchSerializer
from utils.base.exceptions import QueryParseError
from utils.base.general import tup_to_dict
from utils.base.mixins import ListMixinUtils
from utils.base.schema import MessageSchema

from . import serializers


class UserPackageList(generics.ListAPIView):
    """
    Get package list for a user
    """
    serializer_class = serializers.PackageSerializer
    permission_classes = (BasicPerm,)

    def get_queryset(self):
        return Package.objects.filter(
            user__id=self.request.user.id
        ).order_by('cargo_name')


class SearchPackageByTrackingCode(generics.ListAPIView):
    """
    Search for packages using package tracking code
    """
    serializer_class = serializers.PackageSerializer
    permission_classes = (BasicPerm,)

    def get_queryset(self):
        tracking_code = self.request.query_params.get('tracking_code')

        if not tracking_code:
            raise QueryParseError

        return Package.objects.filter(
            user__id=self.request.user.id
        ).filter(
            tracking_code__icontains=tracking_code
        ).order_by('cargo_name')

    @swagger_auto_schema(
        query_serializer=serializers.SearchPackageByTrackingCodeSerializer
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PackageCargoType(views.APIView):
    """
    Get package cargo types
    TODO: Move this to documentations instead of creating
    a view for it
    """
    permission_classes = (BasicPerm,)

    @swagger_auto_schema(
        responses={200: serializers.ManyCargoTypeSerializer}
    )
    def get(self, *args, **kwargs):
        dicts = tup_to_dict(Package.CARGO_TYPE)
        data = {
            'choices': dicts
        }
        return Response(data=data, status=200)


class UserOrderList(generics.ListAPIView):
    """
    Get package orders for a user
    """
    serializer_class = serializers.OrderSerializer
    permission_classes = (BasicPerm,)

    def get_queryset(self):
        """
        Filter the queryset to only orders of logged in user
        """
        return Order.objects.filter(
            package__user__id=self.request.user.id
        ).order_by('package__cargo_name')


class OrderDetailDelete(generics.RetrieveDestroyAPIView):
    """
    Retrieve and delete a user package order
    TODO: Check if this endpoint is necessary
    """
    permission_classes = (BasicPerm,)
    serializer_class = serializers.OrderSerializer
    lookup_field = 'tracking_code'

    def get_queryset(self):
        """
        Filter the queryset to only orders of logged in user
        """
        return Order.objects.filter(package__user__id=self.request.user.id)


class OrdersLogistic(generics.ListAPIView):
    """
    Get logistics recent orders
    """
    permission_classes = (AuthUserIsLogistic,)
    serializer_class = serializers.OrderSerializer

    def get_queryset(self):
        """
        Filter the queryset to only orders from a logistics that logged in as user
        """
        queryset = Order.objects.filter(
            logistic_package__logistic__user__id=self.request.user.id)
        return queryset


class OrdersForPricePackage(generics.ListAPIView):
    """
    Get all orders for a specific price package
    """
    permission_classes = (AuthUserIsLogistic,)
    serializer_class = serializers.OrderSerializer

    def get_queryset(self):
        """
        Filter the queryset to only orders for a specific price package
        by logistic
        """
        tracking_code = self.kwargs['tracking_code']

        queryset = PricePackage.objects.filter(
            logistic=self.request.user.logistic).get(
            tracking_code=tracking_code).order_set.all()

        return queryset


class LogisticsUpdateView(generics.UpdateAPIView):
    """
    update the Logistics instance that is logged in as logistics user
    """
    permission_classes = (AuthUserIsLogistic,)
    serializer_class = serializers.LogisticSerializer

    def get_object(self):
        return self.request.user.logistic


class LogisticsCreateImageView(generics.UpdateAPIView):
    """
    create the Logistics image that is logged in as logistics user
    """
    permission_classes = (AuthUserIsLogistic,)
    serializer_class = serializers.LogisticCreateImageSerializer


    def get_object(self):
        return self.request.user.logistic


class PricePackageCreate(generics.CreateAPIView):
    """
    create route plan
    """
    permission_classes = (AuthUserIsLogistic,)
    serializer_class = serializers.PricePackageRouteSerializer


    def perform_create(self, serializer):
        serializer.save(logistic=self.request.user.logistic)


class PricePackageUpdate(generics.UpdateAPIView):
    """
    update route plan
    """
    permission_classes = (AuthUserIsLogistic,)
    serializer_class = serializers.PricePackageRouteSerializer
    lookup_field = 'tracking_code'

    def get_queryset(self):
        return PricePackage.objects.filter(logistic=self.request.user.logistic)


class PricePackageDelete(generics.DestroyAPIView):
    """
    delete route plan
    """
    permission_classes = (AuthUserIsLogistic,)
    serializer_class = serializers.PricePackageRouteSerializer
    lookup_field = 'tracking_code'

    def get_queryset(self):
        return PricePackage.objects.filter(logistic=self.request.user.logistic)


class PackageCreate(generics.CreateAPIView):
    """
    Create a new package for a user
    """
    serializer_class = serializers.PackageSerializer
    permission_classes = (BasicPerm,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get validated data to get pickup and delivery information
        package_data = serializer.validated_data
        pickup = package_data.get('pickup')
        delivery = package_data.get('delivery')

        # Find price packages (route plans) here
        price_packages = PricePackage.objects.find_logistic(pickup, delivery)

        if price_packages.count() > 0:
            package = self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            package.price_packages.set(price_packages)
            return Response(
                serializer.data, status=status.HTTP_201_CREATED,
                headers=headers)
        else:
            return Response(data=None, status=434)

    def perform_create(self, serializer):
        package = serializer.save(user=self.request.user)
        return package


class GetPricePackages(generics.GenericAPIView):
    """
    Get price packages (route plans) for a package
    """
    serializer_class = serializers.PricePackageSerializer
    permission_classes = (BasicPerm,)

    def get_package_and_price_packages(self):
        tracking_code = self.kwargs.get('tracking_code')
        package = Package.objects.prefetch_related(
            'price_packages', 'price_packages__logistic'
        ).get(tracking_code=tracking_code)
        return package, package.price_packages.all()

    def get(self, *args, **kwargs):
        """
        Get price packages for a package
        """
        package, queryset = self.get_package_and_price_packages()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(
                page, many=True, context={'package': package}
            )
            response_data = self.get_paginated_response(serializer.data).data
            package_serializer = serializers.PackageSerializerWithoutOrder(package)  # noqa
            response_data['package'] = package_serializer.data
            return Response(response_data)

        serializer = self.get_serializer(
            queryset, many=True, context={'package': package}
        )
        return Response(serializer.data)


class SelectLogisticsPackage(generics.GenericAPIView):
    """
    Select price package (route plan) for a package
    """
    serializer_class = serializers.PackageSerializer
    permission_classes = (BasicPerm,)

    def get_price_package_and_package(self):
        package_code = self.request.data.get('package_code')
        price_code = self.request.data.get('price_code')
        package = Package.objects.select_related('order').get(
            tracking_code=package_code)
        price_package = package.price_packages.select_related('logistic').get(
            tracking_code=price_code)
        return package, price_package

    @swagger_auto_schema(
        request_body=serializers.CreateOrderFromPricePackageSerializer,
        responses={
            201: serializers.PackageSerializer
        }
    )
    def post(self, *args, **kwargs):
        package, price_package = self.get_price_package_and_package()

        calc_price = price_package.price * 2 * package.weight * package.quantity  # noqa

        # Check if package already has an order
        try:
            order = package.order

            # Check if transaction is already created
            if order.transaction is not None:
                return Response(data=None, status=435)

            # Delete old order to add new one below
            order.delete()

        except Order.DoesNotExist:
            pass

        # Create order with logistics
        Order.objects.create(
            package=package, price=calc_price,
            logistic_package=price_package)

        # Serialize package
        package_serializer = serializers.PackageSerializer(package)
        return Response(package_serializer.data)


class UserPackageRetrieveUpdate(generics.RetrieveUpdateAPIView):
    """
    Get a user package by it's order tracking code
    """
    permission_classes = (BasicPerm,)
    serializer_class = serializers.PackageSerializer
    lookup_field = 'order__tracking_code'
    lookup_url_kwarg = 'tracking_code'

    http_method_names = ['patch', 'get']

    def get_queryset(self):
        return Package.objects.filter(user__id=self.request.user.id)


class UserPackageRetrieveUpdateByPkg(UserPackageRetrieveUpdate):
    """
    Get a user package by its tracking code
    """
    lookup_field = 'tracking_code'


class SuperUserPackageRetrieveUpdate(UserPackageRetrieveUpdateByPkg):
    """
    Allows only superuser to retrieve, and update a package
    """
    permission_classes = (SuperPerm,)

    def get_queryset(self):
        return Package.objects.all()


class DriverViewSet(ListMixinUtils, viewsets.ModelViewSet):
    """
    Driver endpoints for patner logistics
    """
    serializer_class = serializers.DriverSerializer
    permission_classes = (AuthUserIsLogistic,)
    lookup_field = 'tracking_code'

    def get_queryset(self):
        return Driver.objects.filter(
            logistic=self.request.user.logistic).prefetch_related(
                'user', 'user__profile').order_by('-id')

    @swagger_auto_schema(
        query_serializer=SearchSerializer
    )
    @action(detail=False, methods=['get'])
    def search(self, request, *args, **kwargs):
        """Search drivers by phone number and email"""
        search = request.query_params.get('search', None)
        if search is None:
            return Response(
                {'error': 'Please provide a search parameter'},
                status=400)
        drivers = (self.get_queryset().filter(
            user__profile__phone__icontains=search
        ) | self.get_queryset().filter(
            user__email__icontains=search
        )).distinct()
        return self.get_with_queryset(drivers)

    @action(detail=False, methods=['get'])
    def verified(self, *args, **kwargs):
        """Get verified and active instances"""
        queryset = self.get_queryset().filter(
            verified=True).filter(active=True)
        return self.get_with_queryset(queryset)

    @swagger_auto_schema(
        request_body=serializers.AssignDriverOrderSerializer,
        responses={
            200: MessageSchema
        }
    )
    @action(detail=False, methods=['post'])
    def assign_order(self, request, *args, **kwargs):
        """
        Assign order to a driver
        """
        serializer = serializers\
            .AssignDriverOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            "message": "Success"
        })


class LogisticPackageRetrieve(generics.RetrieveAPIView):
    """
    Get a logistic package by the package tracking code
    """
    permission_classes = (AuthUserIsLogistic,)
    serializer_class = serializers.PackageSerializer
    lookup_field = 'tracking_code'

    def get_queryset(self):
        return Package.objects.filter(
            order__logistic_package__logistic=self.request.user.logistic)
