import os
from openpyxl import Workbook

def generate_excel():
    # 获取当前目录中的所有文件
    files = [f for f in os.listdir('.') if os.path.isfile(f)]

    # 创建一个新的Excel工作簿
    wb = Workbook()

    # 获取默认的工作表
    ws = wb.active

    # 添加标题行
    ws.append(["序号", "文件名"])

    # 添加文件信息
    for index, file in enumerate(files, start=1):
        ws.append([index, file])

    # 保存Excel文件
    wb.save("file_list.xlsx")

if __name__ == "__main__":
    generate_excel()