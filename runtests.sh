#!/bin/sh

cd $(dirname $0)

python -m yiyun.tests.runtests "$@"
