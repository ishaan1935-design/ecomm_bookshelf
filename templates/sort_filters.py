from django import template

register = template.Library()


@register.simple_tag
def selected_if(value, match):
    """Return 'selected' if value equals match"""
    if str(value) == str(match):
        return 'selected'
    return ''


@register.simple_tag
def get_sort_params(request, sort_by, direction):
    """Generate URL parameters with current search and pagination"""
    params = []

    # Preserve search
    search = request.GET.get('search', '')
    if search:
        params.append(f'search={search}')

    # Preserve page
    page = request.GET.get('page', '1')
    if page and page != '1':
        params.append(f'page={page}')

    # Add sort
    params.append(f'sort={sort_by}_{direction}')

    return '&'.join(params)