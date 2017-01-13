FROM registry.cn-beijing.aliyuncs.com/parteam/python3

RUN mkdir -p /var/log/app/

RUN service supervisor stop
RUN echo "daemon off;" >> /etc/nginx/nginx.conf
RUN rm /etc/nginx/sites-enabled/default

# Add nginx.conf
ADD ./docker/nginx.conf /etc/nginx/sites-enabled/app

# Add supervisor
ADD ./docker/supervisord.conf /etc/supervisor/conf.d/app.conf

# Allow Celery to run as root
ENV C_FORCE_ROOT 1

# create /app and add files
ADD . /app
WORKDIR /app
RUN pip install -r requirements.txt -i https://pypi.mirrors.ustc.edu.cn/simple/
# 镜像源可替换为 清华大学  https://pypi.tuna.tsinghua.edu.cn/simple/

EXPOSE 80
VOLUME /var/log/app

CMD ["supervisord"]