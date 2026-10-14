# context_processors.py
def search_context(request):
    """
    Make search and sort parameters available in all templates
    """
    return {
        'search_string': request.GET.get('search', ''),
        'current_sort': request.GET.get('sort', 'title_asc'),
    }

