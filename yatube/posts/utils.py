from django.core.paginator import Paginator
from yatube.settings import POSTS_COUNT
from yatube.settings import POSTS_COUNT


def paginator(request, posts):
    '''Паджинатор'''
    paginator = Paginator(posts, POSTS_COUNT)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
