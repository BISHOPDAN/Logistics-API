from rest_framework.exceptions import ParseError


class QueryParseError(ParseError):
    default_detail = 'Malformed or Incomplete query data'
    default_code = 'baq_query_data'
