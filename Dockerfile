FROM ubuntu:16.04

ENV DEBIAN_FRONTEND noninteractive
COPY ./files/sources.list /etc/apt/sources.list
RUN apt-get update -yqq
RUN apt-get install curl git-core software-properties-common htop build-essential vim supervisor nginx sudo -yqq
RUN apt-get install libtiff5-dev libssl-dev libffi-dev libjpeg8-dev zlib1g-dev libmysqlclient-dev -yqq
RUN apt-get install libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev python-tk -yqq
RUN curl -sL https://deb.nodesource.com/setup_6.x | sudo -E bash -
RUN apt-get install nodejs -y
RUN add-apt-repository ppa:fkrull/deadsnakes -y
RUN apt-get install python3.5 python3.5-dev libncurses5-dev -yqq
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.5 0
RUN curl -sL https://bootstrap.pypa.io/get-pip.py | sudo python -
RUN pip install setuptools --upgrade
RUN pip install pip --upgrade
RUN mkdir -p ~/.pip
COPY ./files/pip.conf ~/.pip/pip.conf
COPY ./files/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
RUN sed -i 's/python/python2/g'  /usr/bin/supervisord
RUN sed -i 's/python/python2/g'  /usr/bin/supervisorctl

RUN echo "export TERM=xterm" >> ~/.bashrc
RUN echo "export DEBIAN_FRONTEND=noninteractive" >> ~/.bashrc

# change tz
# RUN timedatectl set-timezone Asia/Shanghai
RUN rm /etc/localtime
RUN ln -s /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

# some cleanup
RUN apt-get clean
RUN rm -f /tmp/requirements.txt