from django.shortcuts import render


def index(request):
    """
    test1
    """
    context = {
        'data': 'value',
    }
    return render(request, 'index.html', context)
