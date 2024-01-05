import os
import sys
from openpyxl import Workbook

def generate_excel(folder_path):
    # 获取指定文件夹中的所有文件
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

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
    excel_filename = os.path.join(folder_path, "file_list.xlsx")
    wb.save(excel_filename)
    print(f"Excel 文件已保存为: {excel_filename}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python script.py 文件夹路径")
        sys.exit(1)

    folder_path = sys.argv[1]

    if not os.path.exists(folder_path):
        print("指定的文件夹路径不存在。")
        sys.exit(1)

    generate_excel(folder_path)
