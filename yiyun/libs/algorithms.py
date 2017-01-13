"""
排序算法
"""

from math import acos, cos, sin

# 地球半径
EARTH_RADIUS = 6378.137


def latitude_calculator(lat1, lon1, lat2, lon2):
    """
    经纬度距离算法

    :param lat1: 纬度1
    :param lon1: 经度1
    :param lat2:
    :param lon2:
    :return: distance
    """
    return EARTH_RADIUS * \
        acos(cos(lat1)*cos(lat2)*cos(lon2-lon1) + sin(lat1)*sin(lat2))
