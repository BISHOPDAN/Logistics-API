import requests
from django.conf import settings
from rest_framework import status as http_status
from utils.base.general import err_logger


class FlutterwaveClient:
    def __init__(self) -> None:
        self.base_url = 'https://api.flutterwave.com/v3'

    def build_request_args(self):
        headers = {
            'Authorization': f'Bearer {settings.FLW_SECRET_KEY}',
            'Content-Type': 'application/json',
        }
        return headers

    def post(self, endpoint: str, data: dict):
        """
        Initiate a post request to flutterwave
        """
        url = self.base_url + endpoint
        headers = self.build_request_args()

        response = requests.post(headers=headers, url=url, json=data)
        return self.process(response.status_code, response.json())

    def get(self, endpoint: str, query_params: dict = None):
        """
        Initiate a get request to flutterwave
        """
        url = self.base_url + endpoint
        if query_params is None:
            query_params = dict()
        headers = self.build_request_args()

        response = requests.get(headers=headers, url=url, params=query_params)
        return self.process(response.status_code, response.json())

    def process(self, status: int, data: dict):
        if status != http_status.HTTP_200_OK:
            err_logger.exception({
                'status': status,
                'data': data,
                'message': 'An error occured while \
processing flutterwave request'
            })
            return {
                'status': False,
                'data': data
            }

        return {
            'status': True,
            'data': data
        }

    def create_init_transaction(self, email, amount, callback_url, tx_ref):
        """
        Create a payment link url for a user
        """
        data = {
            "amount": amount,
            'redirect_url': callback_url,
            "currency": "NGN",
            'tx_ref': tx_ref,
            "customer": {
                email: email,
            },
            "customizations": {
                "title": settings.FLW_TITLE,
                "logo": settings.FLW_LOGO,
                "description": settings.FLW_DESCRIPTION,
            }
        }
        response = self.post(endpoint="/payments", data=data)
        status = response['status']
        if status:
            return response['data']['link']

    def verify_transaction(self, tx_id, amount) -> bool | None:
        """
        Verify a transaction
        """
        endpoint = f"transactions/{tx_id}/verify"

        response = self.get(endpoint)

        if response['status']:
            data = response['data']["data"]
            status = data['status']
            tx_amount = data['amount']
            currency = data['currency']
            return status == "successful" \
                and tx_amount == amount and currency == "NGN"


payment_client = FlutterwaveClient()
