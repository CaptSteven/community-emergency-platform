from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """统一分页组件。

    默认每页 10 条，前端可以通过 page/page_size 控制页码和每页数量，
    避免列表接口一次性返回过多数据导致浏览器卡顿。
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 200
