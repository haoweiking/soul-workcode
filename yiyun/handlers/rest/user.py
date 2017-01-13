from yiyun.models import User
from .base import (BaseClubAPIHandler, rest_app, ApiException, authenticated,
                   validate_arguments_with)
from .serializers.user import (UserInsecureSerializer, UserSimpleSerializer)
from .schemas import user as schema


@rest_app.route(r"/users/self")
class MyOwnerInfoHandler(BaseClubAPIHandler):
    """获取当前登录用户的信息"""

    @authenticated
    def get(self):
        self.write(UserInsecureSerializer(self.current_user).data)


@rest_app.route(r"/users/(\d+)")
class UserObjectlHandler(BaseClubAPIHandler):
    """
    获取用户
    """
    login_required = False

    def get(self, user_id):
        """获取用户详情"""
        user = User.get_or_404(id=user_id)
        if self.current_user and self.current_user == user:
            serializer = UserInsecureSerializer
        else:
            serializer = UserSimpleSerializer

        data = serializer(instance=user).data
        self.write(data)

    def has_update_permission(self, user):
        if self.current_user == user:
            return True
        raise ApiException(403, "权限错误, 无权修改用户信息")

    @validate_arguments_with(schema.patch_user)
    @authenticated
    def patch(self, user_id):
        user = User.get_or_404(id=user_id)
        self.has_update_permission(user)

        form = self.validated_arguments
        if not form:
            raise ApiException(400, "填写需要修改的属性和值")

        User.update(**form).where(User.id == user_id).execute()
        self.set_status(204)
