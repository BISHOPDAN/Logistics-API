from drf_yasg import openapi
from drf_yasg.inspectors import SwaggerAutoSchema
from drf_yasg.openapi import Schema


MessageSchema = Schema(
    type='object',
    properties={
        'message': Schema(type='string')
    }
)


class BaseSchema(SwaggerAutoSchema):
    def wrap_schema(self, schema):
        """Wrap schema with success, status, message, data and path fields

        :param schema: Schema to wrap
        :type schema: Schema
        :return: Wrapped schema
        :rtype: Schema
        """
        return Schema(
            type='object',
            properties={
                'success': Schema(type='boolean'),
                'status': Schema(type='integer'),
                'message': Schema(type='string'),
                'data': schema,
                'path': Schema(type='string'),
            }
        )

    def get_responses(self):
        """Get responses for swagger,
        wrap all responses with success, status, message, data and path fields

        :return: Responses
        :rtype: openapi.Responses
        """
        response_serializers = self.get_response_serializers()
        data = self.get_response_schemas(response_serializers)
        for code in data.keys():
            try:
                data[code].schema = self.wrap_schema(data[code].schema)
            except AttributeError:
                pass

        # Add 400 response for all methods
        data['400'] = openapi.Response(
            description='Bad request',
            schema=self.wrap_schema(
                Schema(
                    type='object',
                    description='Error message key and value',
                    properties={
                        'key': Schema(
                            type='array',
                            items=Schema(
                                type='string',
                                description='Error messages'
                            )
                        )
                    }
                )
            )
        )

        return openapi.Responses(
            responses=data
        )
