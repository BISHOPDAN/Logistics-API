from django.conf import settings
from utils.base.general import logger, err_logger  # noqa

from typing import Tuple
import requests


class PaystackClient:
    def __init__(self) -> None:
        self.base_url = 'https://api.paystack.co'

    def build_request_args(self):
        headers = {
            'Authorization': 'Bearer %s' % settings.PAYSTACK_SECRET,
            'Content-Type': 'application/json',
            'cache-control': 'no-cache'
        }

        return headers

    def post(self, endpoint: str, data: dict) -> Tuple:
        # Generate full url
        url = self.base_url + endpoint

        # get the headers
        headers = self.build_request_args()

        response = requests.post(headers=headers, url=url, json=data)
        return (response.status_code, response.json())

    def get(self, endpoint: str, query_params: dict = None) -> Tuple:
        # Generate full url
        url = self.base_url + endpoint

        if query_params is None:
            query_params = dict()

        # get the headers
        headers = self.build_request_args()

        response = requests.get(headers=headers, url=url, params=query_params)
        return (response.status_code, response.json())

    def get_banks_list(
        self, country='nigeria', currency='NGN',
        endpoint='/bank'
    ) -> dict:
        query_params = {
            'pay_with_bank': True,
            'country': country,
            'currency': currency,
        }

        result = self.get(endpoint, query_params=query_params)

        if result[0] == 200:
            data = []
            for i in result[1]['data']:
                if i['pay_with_bank'] is True:
                    data.append({'name': i['name'], 'code': i['code']})

            return data
        else:
            raise Exception('Request was not completed')

    def abstract_create_func(self, data: dict, endpoint: str):

        status, data = self.post(endpoint, data=data)

        # Process the first status
        if data['status'] is True:
            response_status = data['status']

            if response_status == 'failed':
                err_logger.exception(data['message'])
                raise Exception(data['message'])

        return data

    # Code to create paystack transaction url
    def create_init_transaction(
        self, email, amount, callback_url='',
        reference='', endpoint='/transaction/initialize'
    ):
        # Covert amount to kobo
        amount = amount * 100

        data = {
            "email": email,
            "amount": amount,
            'callback_url': callback_url,
            'reference': reference,
        }

        return self.abstract_create_func(endpoint=endpoint, data=data)

    # Code to charge authorization code
    def charge_authorization_code(
        self, email, amount, authorization_code,
        endpoint='/transaction/charge_authorization'
    ):
        # Covert amount to kobo
        amount = amount * 100

        data = {
            "email": email,
            "amount": amount,
            'authorization_code': authorization_code,
        }

        return self.abstract_create_func(endpoint=endpoint, data=data)

    # Code to verify paystack transaction ref
    def verify_transaction(
        self, reference='', endpoint='/transaction/verify'
    ):
        # Add the reference to the endpoint
        endpoint = endpoint + '/' + reference

        status, data = self.get(endpoint)

        # Process the first status
        if status == 200:
            response_status = data['status']

            if response_status is True:
                # Get the data returned
                main_data = data['data']
                return (True, main_data,)

            else:
                err_logger.exception(data['message'])

        return (status, data,)

    def create_charge(
        self, email, amount, bank_code, account,
        endpoint='/charge'
    ):
        data = {
            "email": email,
            "amount": amount,
            "bank": {
                'code': bank_code,
                'account_number': account
            },
        }

        return self.abstract_create_func(endpoint=endpoint, data=data)

    def send_birthday(
        self, birthday, reference, endpoint='/charge/submit_birthday'
    ):
        data = {
            "birthday": birthday,
            "reference": reference,
        }

        return self.abstract_create_func(endpoint=endpoint, data=data)

    def submit_pin(self, pin, reference, endpoint='/charge/submit_pin'):
        data = {
            "pin": pin,
            "reference": reference,
        }

        return self.abstract_create_func(endpoint=endpoint, data=data)

    def submit_otp(self, otp, reference, endpoint='/charge/submit_otp'):
        data = {
            "otp": otp,
            "reference": reference,
        }

        return self.abstract_create_func(endpoint=endpoint, data=data)

    def submit_phone(self, phone, reference, endpoint='/charge/submit_phone'):
        data = {
            "phone": phone,
            "reference": reference,
        }

        return self.abstract_create_func(endpoint=endpoint, data=data)

    def submit_address(
        self, address, city, state, zipcode,
        reference, endpoint='/charge/submit_address'
    ):
        data = {
            "address": address,
            "city": city,
            "state": state,
            "zipcode": zipcode,
            "reference": reference,
        }

        return self.abstract_create_func(endpoint=endpoint, data=data)


payment_client = PaystackClient()
