import os
import pandas as pd

# 获取文件夹名称
folder_name = os.path.basename(os.getcwd())

# 创建一个空的数据框
df = pd.DataFrame(columns=['序号', '书名'])

# 读取文件夹中所有文件的名称
files = os.listdir()

# 遍历文件列表
for i, file in enumerate(files):
    # 获取文件的完整路径
    file_path = os.path.join(os.getcwd(), file)

    # 检查文件是否为文件
    if os.path.isfile(file_path):
        # 获取文件的名称，包括后缀
        file_name = os.path.basename(file)

        # 添加一行数据到数据框
        df.loc[i] = [i + 1, file_name]

# 将数据框保存为excel表格
df.to_excel(f'{folder_name}.xlsx', index=False)

# 提示用户
print(f'已将文件夹中所有文件的名称保存至excel表格“{folder_name}.xlsx”中。')