import logging
from django.http.response import HttpResponse

# Instantiate logger.
logger = logging.getLogger(__name__)


def login_request(request):
    """
    Starts Facebook authentication.
    """
    return HttpResponse('Facebook')