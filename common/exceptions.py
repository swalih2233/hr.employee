"""
custom handler
"""
import sys
import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404

from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException, ValidationError
from rest_framework import status
from rest_framework.utils.serializer_helpers import ReturnDict

logger = logging.getLogger(__name__)

class InvalidInputError(APIException):
    """
    Catch for manually raised exceptions and DRF's validation error
    """

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid input sent."
    error_code = "INVALID_INPUT"

class GenericValueError(APIException):
    """
    A catch-all for any exceptions without a specific class.
    """
    status_code = 500
    default_detail = ""
    error_code = "GENERIC_VALUE_ERROR"

class EndpointNotFound(APIException):
    """
    Raised when endpoint isn't found
    """
    status_code = 404
    default_detail = "Endpoint not found."
    error_code = "ENDPOINT_NOT_FOUND"

class AuthenticationFailure(APIException):
    """
    Raised when endpoint isn't found
    """
    status_code = 401
    default_detail = "Authentication failed"
    error_code = "AUTHENTICATION_FAILED"

class MethodNotFound(APIException):
    """
    Raised when endpoint isn't found
    """
    status_code = 405
    default_detail = "Method not allowed"
    error_code = "METHOD_NOT_ALLOWED"

def custom_exception_handler(exc, context):
    if isinstance(exc, ValidationError):
        exc = InvalidInputError(exc.detail)
    # Now add the HTTP status code to the response.
    if isinstance(exc, Http404):
        exc = EndpointNotFound()
    if hasattr(exc, 'detail'):
        error_message = exc.detail
        if type(exc.detail) == ReturnDict:
            error_message = []
            for field, errors in exc.detail.items():
                msg = errors[0].replace('This field', field)
                error_message.append(msg)
            if len(error_message) == 1:
                error_message = error_message[0]
    else:
        error_message = 'Unknown Error'
    if isinstance(exc, Exception) and not isinstance(exc, (Http404, PermissionDenied,
                                                           APIException)):
        logger.exception(exc)
        exc = GenericValueError(error_message)
        tb_type, value, trace = sys.exc_info()
    # Call REST framework's default exception handler
    # to get the standard error response.
    response = exception_handler(exc, context)
    response.data['status'] = response.status_code
    response.data['errors'] = error_message
    return response