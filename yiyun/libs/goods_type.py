import pickle

from yiyun.core import current_app as app


class GoodsTypeToModel(object):
    MAPPING = {}

    def __call__(self, codename):
        return self.get_model(codename)

    def register(self, model, codename):
        """
        将商品 codename -> Model 映射注册到缓存中
        Args:
            model:
            codename:

        Returns:

        """
        self.MAPPING[codename] = model
        setattr(model, 'goods_type', codename)

    def get_model(self, codename):
        """
        通过 codename 获取对应 Model
        Args:
            codename:

        Returns:

        """
        return self.MAPPING.get(codename)


class GoodsTypeToModelRedisCache(object):
    CACHE_KEY = 'yiyun:goods_type_to_model_mapping'

    def register(self, model, codename):
        """
        将商品 codename -> Model 映射注册到缓存中
        Args:
            model:
            codename:

        Returns:

        """
        app.redis.hset(self.CACHE_KEY, codename,
                       pickle.dumps(model, pickle.HIGHEST_PROTOCOL))

    def get_model(self, codename):
        """
        通过 codename 获取对应 Model
        Args:
            codename:

        Returns:

        """

        model = app.redis.hget(self.CACHE_KEY, codename)
        if not model:
            raise IndexError('codename -> Model 映射不存在')
        return pickle.loads(model, pickle.HIGHEST_PROTOCOL)


mapping = GoodsTypeToModel()
