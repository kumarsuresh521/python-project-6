import jwt
from django.http import HttpResponse
import json
import base64
from django.conf import settings

class TokenVerifyMiddleware:
    def __init__(self,get_response):
        self.get_response = get_response

    def __call__(self,request):
        try:
            username = request.session["preferred_username"]
            roles = request.session["roles"]
            request.session['name'] = username
            path = request.path.split('/')

            if "orch" == path[1]:
                uam_path = path[2]
                api_path = path[3]

                if uam_path == "uam" and api_path == "key-cloak-logout":
                        return self.get_response(request)

                if not ("ROLE_ADMIN" in roles or "ROLE_SUPER_ADMIN" in roles or "ROLE_SUPPORT_ADMIN" in roles or "ROLE_READ_ONLY" in roles or "ROLE_IMPORT" in roles):
                    return HttpResponse(json.dumps({"message": 'User is not valid'}), status=401)

                if uam_path == "api" and api_path  in ["verify-document", "document-upload"]:
                    if not ("ROLE_ADMIN" in roles or "ROLE_SUPER_ADMIN" in roles or "ROLE_SUPPORT_ADMIN" in roles or "ROLE_IMPORT" in roles):
                        return HttpResponse(json.dumps({"message": 'User is not valid'}), status=401)

                if uam_path == "uam":
                    if not ("ROLE_ADMIN" in roles or "ROLE_SUPER_ADMIN" in roles or "ROLE_SUPPORT_ADMIN" in roles):
                        return HttpResponse(json.dumps({"message": 'User is not valid'}), status=401)

        except Exception as e:
            return HttpResponse(json.dumps({"message": 'User is not valid'}), status=401)
        return self.get_response(request)
