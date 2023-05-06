from django.core.paginator import Paginator


MAX_NUM_OF_POSTS = 10


def paginator_obj(request, posts):
    paginator = Paginator(posts, MAX_NUM_OF_POSTS)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
