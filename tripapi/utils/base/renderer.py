from rest_framework.renderers import (INDENT_SEPARATORS, LONG_SEPARATORS,
                                      SHORT_SEPARATORS, JSONRenderer)
from rest_framework.utils import json

from .general import DecorResponse


class ApiRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Render `data` into JSON, returning a bytestring.

        Used restframework main code and edited it
        """

        # Customize the response
        request = renderer_context.get('request')
        response = renderer_context.get('response')
        data = DecorResponse(
            request=request,
            status=response.status_code,
            data=response.data).response()

        if data is None:
            return b''

        renderer_context = renderer_context or {}
        indent = self.get_indent(accepted_media_type, renderer_context)

        if indent is None:
            separators = SHORT_SEPARATORS if self.compact else LONG_SEPARATORS
        else:
            separators = INDENT_SEPARATORS

        ret = json.dumps(
            data, cls=self.encoder_class,
            indent=indent, ensure_ascii=self.ensure_ascii,
            allow_nan=not self.strict, separators=separators
        )

        # We always fully escape \u2028 and \u2029 to ensure we output JSON
        # that is a strict javascript subset.
        # See: http://timelessrepo.com/json-isnt-a-javascript-subset
        ret = ret.replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
        return ret.encode()
