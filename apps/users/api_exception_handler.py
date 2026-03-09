from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_api_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return response

    if response.status_code in (401, 403):
        detail = response.data.get('detail', 'Access denied.')
        return Response(
            {
                'access': False,
                'message': str(detail),
                'hint': 'Use an account with the required role for this endpoint.',
            },
            status=status.HTTP_200_OK,
        )

    return response
