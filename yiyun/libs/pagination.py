# coding: utf-8

from math import ceil


class Pagination(object):

    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total_count = total_count

    @property
    def info(self):
        return {
            "page": self.page,
            "per_page": self.per_page,
            "total_count": self.total_count,
            "pages": self.pages
        }

    @property
    def pages(self):
        return int(ceil(self.total_count / float(self.per_page)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and
                num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num


class Page(object):
    """
    分页, 可迭代对象
    Django-like
    """

    def __init__(self, object_list, number, paginator):
        self.object_list = object_list
        self.number = number
        self.paginator = paginator

    def __iter__(self):
        i = 0
        try:
            while True:
                v = self[i]
                yield v
                i += 1
        except IndexError:
            return

    def __contains__(self, value):
        for v in self:
            if v == value:
                return True
        return False

    def __reversed__(self):
        for i in reversed(range(len(self))):
            yield self[i]

    def __repr__(self):
        return '<Page {0} or {1}'.format(self.number, self.paginator.num_pages)

    def __len__(self):
        return len(self.object_list)

    def __getitem__(self, item):
        return self.object_list[item]

    def has_next(self):
        return self.number < self.paginator.num_pages

    def has_previous(self):
        return self.number > 1

    def has_other_pages(self):
        return self.has_previous() or self.has_next()

    def previous_page_number(self):
        if self.has_previous():
            return self.number - 1
        else:
            return None

    def next_page_number(self):
        if self.has_next():
            return self.number + 1
        else:
            return None


class Paginator(object):
    """
    分页处理方法
    Django-like
    """

    def __init__(self, object_list, per_page, *args, **kwargs):
        self.object_list = object_list
        self.per_page = per_page
        self._count = self._num_pages = None
        self.allow_empty_first_page = True

    def validate_number(self, number):
        """
        校验页码是否正确
        Args:
            number:

        Returns:

        """
        try:
            number = int(number)
        except (TypeError, ValueError):
            raise ValueError('That page number is not an integer')
        if number < 1:
            raise ValueError('That page number is less than 1')
        if number > self.num_pages:
            if number == 1 and self.allow_empty_first_page:
                pass
            else:
                raise ValueError('That page contains no results')
        return number

    def _get_count(self):
        """
        total count
        Returns: int

        """
        if self._count is None:
            try:
                self._count = self.object_list.count()
            except (AttributeError, TypeError):
                self._count = len(self.object_list)
        return self._count
    count = property(_get_count)

    def _get_num_pages(self):
        """
        return total number of pages.
        Returns: int
        """
        if self._num_pages is None:
            if self.count == 0:
                self._num_pages = 0
            else:
                hits = max(1, self.count)
                self._num_pages = int(ceil(hits / float(self.per_page)))
        return self._num_pages
    num_pages = property(_get_num_pages)

    def page(self, number):
        """
        返回指定页
        Args:
            number:

        Returns: Page()

        """
        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page
        if top >= self.count:
            top = self.count
        return self._get_page(self.object_list[bottom:top], number, self)

    def _get_page(self, *args, **kwargs):
        return Page(*args, **kwargs)
