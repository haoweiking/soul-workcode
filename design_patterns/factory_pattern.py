# 工厂模式 解决对象创建问题
import os
import json
import xml.etree.ElementTree as etree


class JSONConnector:
    def __init__(self, filepath):
        self.data = dict()
        with open(filepath, mode='r', encoding='utf8') as f:
            self.data = json.load(f)

    @property
    def parsed_data(self):
        return self.data


class XMLConnector:
    def __init__(self, filepath):
        self.tree = etree.parse(filepath)

    @property
    def parsed_data(self):
        return self.tree


def connection_factory(filepath):
    """工厂方法"""
    if filepath.endswith('json'):
        connector = JSONConnector
    elif filepath.endswitch('xml'):
        connector = XMLConnector
    else:
        raise ValueError('Cannot connect to {}.'.format(filepath))
    return connector(filepath)

if __name__ == '__main__':
    path = os.getcwd()
    file = open(path + "/design_patterns/factory_pattern.json", 'r')
    connection_factory(file)
    file = open(path + "/design_patterns/factory_pattern.xml", 'r')
