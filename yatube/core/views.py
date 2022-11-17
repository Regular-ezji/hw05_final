from django.shortcuts import render


def page_not_found(request, exception):
    template = 'core/404.html'
    return render(request, template, {'path': request.path}, status=404)


def permission_denied_view(request, exception):
    template = 'core/403csrf.html'
    return render(request, template, {'path': request.path}, status=403)


def internal_server_error(request, exception):
    template = 'core/500.html'
    return render(request, template, {'path': request.path}, status=403)
