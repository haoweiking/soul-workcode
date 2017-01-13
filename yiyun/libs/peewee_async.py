"""
peewee-async
============
ported from peewee-async(https://github.com/05bit/peewee-async)

"""
import asyncio
import aiomysql
import peewee
import playhouse.pool
import contextlib
from playhouse.shortcuts import RetryOperationalError

__version__ = '0.1'

__all__ = [
    # Database backends
    'MySQLDatabase',
    'RetryMySQLDatabase',
    'PooledMysqlDatabase',

    # Sync calls helpers
    'sync_unwanted',
    'UnwantedSyncQueryError',
]


class AsyncQueryMixin:
    """docstring for AsyncQueryMixin"""

    @asyncio.coroutine
    def async_execute(self, query):
        """Execute *SELECT*, *INSERT*, *UPDATE* or *DELETE* query asyncronously.

        :param query: peewee query instance created with ``Model.select()``,
                      ``Model.update()`` etc.
        :return: result depends on query type, it's the same as for sync ``query.execute()``
        """
        if isinstance(query, peewee.UpdateQuery):
            coroutine = "async_update"
        elif isinstance(query, peewee.InsertQuery):
            coroutine = "async_insert"
        elif isinstance(query, peewee.DeleteQuery):
            coroutine = "async_delete"
        else:
            coroutine = "async_select"

        return (yield from getattr(self, coroutine)(query))

    @asyncio.coroutine
    def async_create_object(self, model, **data):
        """Create object asynchronously.

        :param model: mode class
        :param data: data for initializing object
        :return: new object saved to database
        """
        obj = model(**data)

        # NOTE! Here are internals involved:
        #
        # - obj._data
        # - obj._dirty
        # - obj._get_pk_value()
        # - obj._set_pk_value()
        #
        field_dict = dict(obj._data)
        pk = obj.get_id()
        pk_from_cursor = yield from self.async_insert(obj.insert(**field_dict))
        if pk_from_cursor is not None:
            pk = pk_from_cursor
        obj.set_id(pk)  # Do not overwrite current ID with None.

        obj._dirty.clear()
        obj.prepared()

        return obj

    @asyncio.coroutine
    def async_get_object(self, source, *args):
        """Get object asynchronously.

        :param source: mode class or query to get object from
        :param args: lookup parameters
        :return: model instance or raises ``peewee.DoesNotExist`` if object not found
        """
        if isinstance(source, peewee.Query):
            base_query = source
            model = base_query.model_class
        else:
            base_query = source.select()
            model = source

        # Return first object from query
        for obj in (yield from self.async_select(base_query.where(*args).limit(1))):
            return obj

        # No objects found
        raise model.DoesNotExist

    @asyncio.coroutine
    def async_delete_object(obj, recursive=False, delete_nullable=False):
        """Delete object asynchronously.

        :param obj: object to delete
        :param recursive: if ``True`` also delete all other objects depends on object
        :param delete_nullable: if `True` and delete is recursive then delete even 'nullable' dependencies

        For details please check out `Model.delete_instance()`_ in peewee docs.

        .. _Model.delete_instance(): http://peewee.readthedocs.org/en/latest/peewee/api.html#Model.delete_instance
        """
        # Here are private calls involved:
        # - obj._pk_expr()
        if recursive:
            dependencies = obj.dependencies(delete_nullable)
            for query, fk in reversed(list(dependencies)):
                model = fk.model_class
                if fk.null and not delete_nullable:
                    yield from self.async_update(model.update(**{fk.name: None}).where(query))
                else:
                    yield from self.async_delete(model.delete().where(query))
        result = yield from self.async_delete(obj.delete().where(obj._pk_expr()))
        return result

    @asyncio.coroutine
    def async_update_object(self, obj, only=None):
        """Update object asynchronously.

        :param obj: object to update
        :param only: list or tuple of fields to updata, is `None` then all fields updated

        This function does the same as `Model.save()`_ for already saved object, but it
        doesn't invoke ``save()`` method on model class. That is important to know if you
        overrided save method for your model.

        .. _Model.save(): http://peewee.readthedocs.org/en/latest/peewee/api.html#Model.save
        """
        # Here are private calls involved:
        #
        # - obj._data
        # - obj._meta
        # - obj._prune_fields()
        # - obj._pk_expr()
        # - obj._dirty.clear()
        #
        field_dict = dict(obj._data)
        pk_field = obj._meta.primary_key

        if only:
            field_dict = obj._prune_fields(field_dict, only)

        if not isinstance(pk_field, peewee.CompositeKey):
            field_dict.pop(pk_field.name, None)
        else:
            field_dict = obj._prune_fields(field_dict, obj.dirty_fields)
        rows = yield from self.async_update(obj.update(**field_dict).where(obj._pk_expr()))

        obj._dirty.clear()
        return rows

    @asyncio.coroutine
    def async_select(self, query):
        """Perform SELECT query asynchronously.

        NOTE! It relies on internal peewee logic for generating
        results from queries and well, a bit hacky.
        """
        assert isinstance(query, peewee.SelectQuery),\
            ("Error, trying to run select coroutine"
             "with wrong query class %s" % str(query))

        # Perform *real* async query
        query = query.clone()
        cursor = yield from _execute_query_async(query)

        # Perform *fake* query: we only need a result wrapper
        # here, not the query result itself:
        query._execute = lambda: None
        result_wrapper = query.execute()

        # Fetch result
        result = AsyncQueryResult(result_wrapper=result_wrapper, cursor=cursor)
        try:
            while True:
                yield from result.fetchone()
        except GeneratorExit:
            pass

        # Release cursor and return
        cursor.release()
        return result

    @asyncio.coroutine
    def async_insert(self, query):
        """Perform INSERT query asynchronously. Returns last insert ID.
        """
        assert isinstance(query, peewee.InsertQuery),\
            ("Error, trying to run insert coroutine"
             "with wrong query class %s" % str(query))

        cursor = yield from _execute_query_async(query)
        result = cursor.lastrowid

        cursor.release()
        return result

    @asyncio.coroutine
    def async_update(self, query):
        """Perform UPDATE query asynchronously. Returns number of rows updated.
        """
        assert isinstance(query, peewee.UpdateQuery),\
            ("Error, trying to run update coroutine"
             "with wrong query class %s" % str(query))

        cursor = yield from _execute_query_async(query)
        rowcount = cursor.rowcount

        cursor.release()
        return rowcount

    @asyncio.coroutine
    def async_delete(self, query):
        """Perform DELETE query asynchronously. Returns number of rows deleted.
        """
        assert isinstance(query, peewee.DeleteQuery),\
            ("Error, trying to run delete coroutine"
             "with wrong query class %s" % str(query))

        cursor = yield from _execute_query_async(query)
        rowcount = cursor.rowcount

        cursor.release()
        return rowcount

    @asyncio.coroutine
    def async_count(self, query, clear_limit=False):
        """Perform *COUNT* aggregated query asynchronously.

        :return: number of objects in ``select()`` query
        """
        if query._distinct or query._group_by or query._limit or query._offset:
            # wrapped_count()
            clone = query.order_by()
            if clear_limit:
                clone._limit = clone._offset = None

            sql, params = clone.sql()
            wrapped = 'SELECT COUNT(1) FROM (%s) AS wrapped_select' % sql
            raw_query = query.model_class.raw(wrapped, *params)
            return (yield from self.async_scalar(raw_query)) or 0
        else:
            # simple count()
            query = query.order_by()
            query._select = [peewee.fn.Count(peewee.SQL('*'))]
            return (yield from self.async_scalar(query)) or 0

    @asyncio.coroutine
    def async_scalar(self, query, as_tuple=False):
        """Get single value from ``select()`` query, i.e. for aggregation.

        :return: result is the same as after sync ``query.scalar()`` call
        """
        cursor = yield from _execute_query_async(query)
        row = yield from cursor.fetchone()

        cursor.release()

        if row and not as_tuple:
            return row[0]
        else:
            return row


class AsyncQueryResult:
    """Async query results wrapper for async `select()`. Internally uses
    results wrapper produced by sync peewee select query.

    Arguments:

        result_wrapper -- empty results wrapper produced by sync `execute()`
        call cursor -- async cursor just executed query

    To retrieve results after async fetching just iterate over this class
    instance, like you generally iterate over sync results wrapper.
    """

    def __init__(self, result_wrapper=None, cursor=None):
        self._result = []
        self._initialized = False
        self._result_wrapper = result_wrapper
        self._cursor = cursor

    def __iter__(self):
        return iter(self._result)

    def __getitem__(self, key):
        return self._result[key]

    def __len__(self):
        return len(self._result)

    @asyncio.coroutine
    def fetchone(self):
        row = yield from self._cursor.fetchone()

        if not row:
            self._cursor = None
            self._result_wrapper = None
            raise GeneratorExit
        elif not self._initialized:
            self._result_wrapper.initialize(self._cursor.description)
            self._initialized = True

        obj = self._result_wrapper.process_row(row)
        self._result.append(obj)


class AsyncConnection:
    """Asynchronous single database connection wrapper.
    """

    def __init__(self, loop, database, host, user, passwd, port=3306, **kwargs):
        self._conn = None
        self._loop = loop if loop else asyncio.get_event_loop()
        self.database = database
        self.host = host
        self.port = port
        self.user = user
        self.password = passwd
        self.connect_kwargs = kwargs

    @asyncio.coroutine
    def connect(self):
        """Connect asynchronously.
        """

        self._conn = yield from aiomysql.connect(host=self.host,
                                                 port=self.port,
                                                 user=self.user,
                                                 password=self.password,
                                                 db=self.database,
                                                 loop=self._loop,
                                                 **self.connect_kwargs)

    @asyncio.coroutine
    def cursor(self, *args, **kwargs):
        """Get connection cursor asynchronously.
        """
        if self._conn.closed:
            yield from self.connect()

        cursor = yield from self._conn.cursor(*args, **kwargs)
        cursor.release = lambda: None
        return cursor

    def close(self):
        """Close connection.
        """
        self._conn.close()


class PooledAsyncConnection:
    """
    Asynchronous database connection pool wrapper.
    """

    def __init__(self, loop, database, host, user, passwd, port=3306, **kwargs):
        self._pool = None
        self._loop = loop if loop else asyncio.get_event_loop()
        self.database = database
        self.host = host
        self.user = user
        self.password = passwd
        self.port = port
        self.connect_kwargs = kwargs

    @asyncio.coroutine
    def connect(self):
        """Create connection pool asynchronously.
        """
        self._pool = yield from aiomysql.create_pool(host=self.host,
                                                     port=self.port,
                                                     user=self.user,
                                                     password=self.password,
                                                     db=self.database,
                                                     loop=self._loop,
                                                     **self.connect_kwargs)

    @asyncio.coroutine
    def cursor(self, *args, **kwargs):
        """Get cursor for connection from pool.
        """
        conn = yield from self._pool.acquire()
        cursor = yield from conn.cursor(*args, **kwargs)
        cursor.release = lambda: all((cursor.close(), self._pool.release(conn)))
        return cursor

    def close(self):
        """Terminate all pool connections.
        """
        self._pool.terminate()


class AsyncMysqlMixin:
    """Mixin for peewee database class providing extra methods
    for managing async connection.
    """

    def init_async(self, conn_cls=AsyncConnection, **kwargs):
        self.allow_sync = True

        self._loop = None
        self._async_conn = None
        self._async_conn_cls = conn_cls
        self._async_kwargs = {}
        self._async_kwargs.update(kwargs)

    @asyncio.coroutine
    def connect_async(self, loop=None, timeout=None):
        """Set up async connection on specified event loop or
        on default event loop.
        """
        if not self._async_conn:
            self._loop = loop if loop else asyncio.get_event_loop()
            self._async_conn = self._async_conn_cls(
                self._loop,
                self.database,
                **self._async_kwargs)
            yield from self._async_conn.connect()

    def close(self):
        """Close both sync and async connections.
        """
        super().close()

        if self._async_conn:
            self._async_conn.close()
            self._async_conn = None
            self._loop = None

    def execute_sql(self, *args, **kwargs):
        """Sync execute SQL query. If this query is performing within
        `sync_unwanted()` context, then `UnwantedSyncQueryError` exception
        is raised.
        """
        if not self.allow_sync:
            raise UnwantedSyncQueryError("Error, unwanted sync query",
                                         args, kwargs)
        return super().execute_sql(*args, **kwargs)


class MySQLDatabase(AsyncMysqlMixin, AsyncQueryMixin, peewee.MySQLDatabase):
    """Mysql database driver providing **single drop-in sync** connection
    and **single async connection** interface.

    See also:
    http://peewee.readthedocs.org/en/latest/peewee/api.html#MySQLDatabase
    """

    def __init__(self, database, threadlocals=True, autocommit=True,
                 fields=None, ops=None, autorollback=True, **kwargs):
        super().__init__(database, threadlocals=True, autocommit=autocommit,
                         fields=fields, ops=ops, autorollback=autorollback,
                         **kwargs)

        connect_kwargs = {
            "autocommit": autocommit
        }
        connect_kwargs.update(self.connect_kwargs)

        self.init_async(**connect_kwargs)


class PooledMySQLDatabase(AsyncMysqlMixin, AsyncQueryMixin, playhouse.pool.PooledMySQLDatabase):
    """Mysql database driver providing **single drop-in sync**
    connection and **async connections pool** interface.

    :param max_connections: connections pool size

    See also:
    http://peewee.readthedocs.org/en/latest/peewee/api.html#MySQLDatabase
    """

    def __init__(self, database, threadlocals=True, autocommit=True,
                 fields=None, ops=None, autorollback=True, max_connections=20,
                 stale_timeout=1800, **kwargs):
        super().__init__(database, threadlocals=True, autocommit=autocommit,
                         fields=fields, ops=ops, autorollback=autorollback,
                         stale_timeout=stale_timeout, max_connections=max_connections,
                         **kwargs)

        connect_kwargs = {
            "autocommit": autocommit
        }
        connect_kwargs.update(self.connect_kwargs)

        self.init_async(conn_cls=PooledAsyncConnection, minsize=1,
                        maxsize=max_connections, **connect_kwargs)


class RetryMySQLDatabase(MySQLDatabase, RetryOperationalError):
    """docstring for RetryMySQLDatabase"""

    pass


@contextlib.contextmanager
def sync_unwanted(database):
    """Context manager for preventing unwanted sync queries.
    `UnwantedSyncQueryError` exception will raise on such query.
    """
    old_allow_sync = database.allow_sync
    database.allow_sync = False
    yield
    database.allow_sync = old_allow_sync


class UnwantedSyncQueryError(Exception):
    """Exception which is raised when performing unwanted sync query.
    """
    pass


@asyncio.coroutine
def _execute_query_async(query):
    """Execute query and return cursor object.
    """
    db = query.database
    assert db._async_conn, "Error, no async database connection."
    cursor = yield from db._async_conn.cursor()
    try:
        yield from cursor.execute(*query.sql())
    except Exception as e:
        cursor.release()
        raise e
    return cursor
