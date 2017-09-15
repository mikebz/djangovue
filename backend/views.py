from django.shortcuts import render


def index(request):
    """
    serving up the main app page which loads the Vue.js from WebPack
    """
    context = {
        'data': 'value',
    }
    return render(request, 'index.html', context)
