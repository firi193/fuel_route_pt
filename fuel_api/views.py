from django.http import JsonResponse
from .utils import get_route_with_stops

def fuel_route_view(request):
    start = request.GET.get('start')  # e.g. "New York, NY"
    end = request.GET.get('end')      # e.g. "Chicago, IL"
    if not start or not end:
        return JsonResponse({'error': 'Missing start or end location'}, status=400)

    result = get_route_with_stops(start, end, request)
    return JsonResponse(result)
