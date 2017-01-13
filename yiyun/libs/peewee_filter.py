from enum import Enum
from peewee import Func, Expression
from peewee import Field as PeeweeField


class FilterException(Exception):

    def __init__(self, msg, *args, **kwargs):
        self.msg = self.message = msg
        super(FilterException, self).__init__(msg, *args, **kwargs)


class MetaOption(object):

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class Filtering(object):
    def __init__(self, source, required=False, default=None, **kwargs):
        self.source = source
        self.required = required
        self.default = default
        self.lookup_type = kwargs.pop('lookup_type', None)
        for key, value in kwargs.items():
            setattr(self, key, value)

    @property
    def lookup_field(self):
        return self._lookup_field()

    def _lookup_field(self):
        if self.lookup_type:
            return '{source}__{lookup_type}'\
                .format(source=self.source, lookup_type=self.lookup_type)
        return self.source

    def value_translator(self, value):
        """
        将传入的 `value` 按照映射转换成对应值用于模型内部查询
        :param value: 待转换的值
        :return:
        """
        return value

    def filter_statement(self, condition):
        """
        生成过滤器查询条件,
        eg. `user_name = "test"`

        :param condition:
        :return:
        """
        value = self.value_translator(condition)
        if isinstance(self.source, PeeweeField):
            if self.lookup_type == 'gte':
                return self.lookup_field >= value
            elif self.lookup_type == 'lte':
                return self.lookup_field <= value
            else:
                return self.lookup_field == value
        else:
            return {self.lookup_field: value}


class NumberFiltering(Filtering):
    pass


class StringFiltering(Filtering):
    pass


class EnumFiltering(Filtering):

    def __init__(self, source, enum_class, *args, **kwargs):
        assert isinstance(enum_class, Enum), \
            "`enum_class` must be a subclass of Enum"
        self.enum_class = enum_class
        super(EnumFiltering, self).__init__(source, *args, **kwargs)

    def value_translator(self, value):
        try:
            translated = self.enum_class.__members__[value]
        except KeyError as e:
            _choices = [key for key in self.enum_class.__members__.keys()]
            choices = ", ".join(map(lambda i: "`{0}`".format(i), _choices))
            raise FilterException("过滤条件只能是: ({0})".format(choices))
        return translated.value


class PWFuncCondition(Filtering):
    """
    使用 peewee.fn 构造条件查询

     eg: today = datetime.datetime.today().date()
         query.filter(fn.date(Activity.start_time) == today)
    """
    pass


class DateCondition(PWFuncCondition):

    def __init__(self, source, **kwargs):
        self.function = kwargs.pop('function', None)
        super(DateCondition, self).__init__(source=source, **kwargs)

    def _lookup_field(self):
        return self.function(self.source)


class ForeignKeyFiltering(NumberFiltering):

    def __init__(self, source, foreign_field='id', **kwargs):
        self.foreign_field = foreign_field
        super(ForeignKeyFiltering, self).__init__(source, **kwargs)

    def _lookup_field(self):
        field = '{source}__{foreign}'\
            .format(source=self.source, foreign=self.foreign_field)
        if self.lookup_type:
            return '{field}__{lookup_type}'\
                .format(field=field, lookup_type=self.lookup_type)
        return field


class SoftForeignKeyFiltering(ForeignKeyFiltering):
    """
    适用于 IntegerField 类型的外键
    """

    def __init__(self, function=None, *args, **kwargs):
        self.function = function
        super(SoftForeignKeyFiltering, self).__init__(*args, **kwargs)

    def _lookup_field(self):
        return getattr(self.source, self.foreign_field)

    def filter_statement(self, condition):
        value = self.value_translator(condition)
        if self.function:
            return getattr(self.lookup_field, self.function)(value)

        if self.lookup_type == "gte":
            return self.lookup_field >= value
        elif self.lookup_type == "lte":
            return self.lookup_field <= value
        else:
            return self.lookup_field == value


class FilterMetaClass(type):

    def __new__(mcs, name, bases, attrs):
        if not bases:
            return super(FilterMetaClass, mcs).__new__(mcs, name, bases, attrs)

        attrs['_declared_fields'] = mcs._get_declared_fields(bases, attrs)
        attrs['_meta'] = mcs._get_meta_options(bases, attrs)
        return super(FilterMetaClass, mcs).__new__(mcs, name, bases, attrs)

    @classmethod
    def _get_meta_options(mcs, bases, attrs):
        meta_options = {}
        meta = attrs.pop('Meta', None)
        if meta:
            for k, v in meta.__dict__.items():
                if not k.startswith('_'):
                    meta_options[k] = v

        # for b in bases:
        #     if not hasattr(b, 'Meta'):
        #         continue
        return MetaOption(**meta_options)

    @classmethod
    def _get_declared_fields(mcs, bases, attrs):
        fields = [(field_name, attrs.pop(field_name)) for field_name, obj in
                  list(attrs.items()) if isinstance(obj, Filtering)]

        for base in reversed(bases):
            if hasattr(base, '_declared_fields'):
                fields = list(base._declared_fields.items()) + fields
        return dict(fields)


class BaseFilter(object, metaclass=FilterMetaClass):

    def __init__(self, query, query_params: dict):
        """

        Args:
            query_params: 用来过滤查询结果的条件,
            query: peewee.SelectQuery

        Returns:

        """
        self.query_params = query_params
        self._query = query

    def _get_query_params(self, key):
        params_value = self.query_params[key]
        # tornado.httputil.HTTPServerRequest compatible
        if isinstance(params_value, (tuple, list)):
            params_value = params_value[-1]
        return params_value

    @property
    def cleaning_params(self):
        if hasattr(self, '_cleaning'):
            return self._cleaning

        self._clean_params()
        return self._cleaning

    @property
    def conditions(self):
        if hasattr(self, '_conditions'):
            return self._conditions
        self._clean_params()
        return self._conditions

    def _clean_params(self):
        kw_params = {}
        _conditions = []
        meta_fields = self._meta.fields
        declared_fields = self._declared_fields
        see = {*meta_fields}.intersection(self.query_params.keys())
        for field in see:

            # # 如果使用 PWFuncCondition 需要额外处理
            # if field in declared_fields and \
            #         isinstance(declared_fields[field], PWFuncCondition):
            #     params_value = self._get_query_params(field)
            #
            #     _field = declared_fields[field]
            #     if _field.lookup_type == 'gte':
            #         _conditions.append(_field.lookup_field >= params_value)
            #     elif _field.lookup_type == 'lte':
            #         _conditions.append(_field.lookup_field <= params_value)
            #     else:
            #         _conditions.append(_field.lookup_field == params_value)
            #
            # elif field in declared_fields:
            #     params_value = self._get_query_params(field)
            #     kw_params[declared_fields[field].lookup_field] = params_value
            # else:
            #     kw_params[field] = self._get_query_params(field)

            params_value = self._get_query_params(field)
            if field in declared_fields:
                statement = declared_fields[field].filter_statement(params_value)
            else:
                statement = {field: params_value}

            if isinstance(statement, dict):
                kw_params.update(statement)
            elif isinstance(statement, Expression):
                _conditions.append(statement)

        self._cleaning = kw_params
        self._conditions = _conditions

    def apply_filter(self):
        """
        应用过滤条件后的 peewee.Query
        Returns:

        """
        raise NotImplementedError()

    @property
    def q(self):
        """
        获取过滤后的 peewee.Query
        Returns: peewee.Query

        """
        return self.apply_filter()


class Filter(BaseFilter):

    def apply_filter(self):
        """
        应用过滤条件后的 peewee.Query
        Returns:

        """
        query = self._query
        if self.cleaning_params:
            query = query.filter(**self.cleaning_params)
        if self.conditions:
            query = query.filter(*self.conditions)
        return query


class SortFilter(Filter):

    @property
    def cleaning_params(self):
        """
        过滤 sort 参数, 只允许 fields 中设置的值
        """
        cleaning = []
        sort = self.query_params.get('sort', None)
        if isinstance(sort, (tuple, list)):
            sort = sort[-1]
        if sort:
            if isinstance(sort, bytes):
                sort = sort.decode()
            sorting_fields = sort.split(',')

            for field in sorting_fields:
                if field.lstrip('-') in self._meta.fields:
                    cleaning.append(field)

        return cleaning

    @property
    def sorting_fields(self):
        sorting = []
        cleaning = self.cleaning_params

        declared_fields = self._declared_fields

        def append_sorting(fields):
            for field in fields:
                if field.startswith('-'):
                    field = field.lstrip('-')
                    sorting.append(-declared_fields[field].source)
                else:
                    sorting.append(declared_fields[field].source)

        append_sorting(cleaning or self._meta.ordering)
        return sorting

    def apply_filter(self):
        return self._query.order_by(*self.sorting_fields)
