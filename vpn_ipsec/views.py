from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
import json
from django.shortcuts import render

@csrf_exempt
def get_config(request):
    if request.method == 'GET':
        demo_response = {
            "code": 200,
            "data": {
                "service": "enable",
                "remote_mg_ip": "10.0.0.5",
                "remote_subnet": "192.168.2.0/24",
                "remote_wan_ip": "10.23.15.33",
                "local_mg_ip": "10.0.0.6",
                "local_wan_ip": "10.23.15.33",
                "local_subnet": "192.168.13.5/24",
                "status": "connected"
            }
        }
        return JsonResponse(demo_response)
    return HttpResponseBadRequest('Invalid method')
 
# @csrf_exempt
# def set_config(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             print("Received data:", data)
#             # Just return dummy success response
#             return JsonResponse({"code": 200})
#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=500)
#     return HttpResponseBadRequest('Invalid method')

def config_form(request):
    return render(request, 'vpn_ipsec/config_form.html')

@csrf_exempt
def set_config(request):
    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST.dict()
            print("Received data:", data)
            return JsonResponse({"code": 200})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return HttpResponseBadRequest('Invalid method')