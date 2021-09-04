from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.conf import settings
from .utils import *

class ApplicationMiddlewares(MiddlewareMixin):
    def __init__(self,get_response):
        self.get_response = get_response
        
    def __call__(self,request):
        cprint("Application Authorization Values")
        cprint(request.session["X-KC-Token"])
        cprint(request.session["preferred_username"])
        cprint(request.session["roles"])
        cprint(request.session["groups"])
        
        return self.get_response(request)