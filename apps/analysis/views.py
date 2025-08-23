from django.shortcuts import render
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import os

@csrf_exempt
def catalog_data_view(request):
    json_path = os.path.join(settings.MEDIA_ROOT, 'analysis/hp/catalog_data.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return JsonResponse(data)
    except FileNotFoundError:
        return JsonResponse(None, status=404)
    except Exception as e:
        return JsonResponse(None, status=500)

@csrf_exempt
def report_data_view(request):
    json_path = os.path.join(settings.MEDIA_ROOT, 'analysis/hp/report_data.json')
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        return JsonResponse(data)
    except FileNotFoundError:
        return JsonResponse(None, status=404)
    except Exception as e:
        return JsonResponse(None, status=500)

@csrf_exempt
def summary_data_view(request):
    json_path = os.path.join(settings.MEDIA_ROOT, 'analysis/hp/summary_data.json')
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        return JsonResponse(data)
    except FileNotFoundError:
        return JsonResponse(None, status=404)
    except Exception as e:
        return JsonResponse(None, status=500)

@csrf_exempt
def reports_data_tree_view(request):
    json_path = os.path.join(settings.MEDIA_ROOT, 'analysis/hp/reports_data_tree.json')
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        return JsonResponse(data)
    except FileNotFoundError:
        return JsonResponse(None, status=404)
    except Exception as e:
        return JsonResponse(None, status=500)
