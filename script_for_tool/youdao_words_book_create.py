# python3 
# 有道词典 单词本生成xml文件
# def is_chinese(uchar):
#     if uchar >= u'\u4e00' and uchar <= u'\u9fa5':
#         return True
#     else:
#         return False

# def get_content(content):
#     for i in range(len(content)):
#         if is_chinese(content[i]):
#             return content[:i], content[i:]


infopen = open("reading.txt",'r',encoding='utf-8') #要读取的txt文件reading.txt
lines = infopen.readlines()
xml_file = open(('reading1.xml'), 'w') #生成的xml文件
xml_file.write('<wordbook>')
for line  in range(len(lines)-1):
    if line % 2 == 0:
        xml_file.write('<item>')
        xml_file.write('    <word>' + lines[line+1].strip('\n') + '</word>\n')
        xml_file.write('    <trans>' + '<![CDATA[' + lines[line].strip('\n') + ']]>' +  '</trans>\n')
        xml_file.write('    <tags>reading</tags>\n') #reading是你单词本的名字，你可以改成自己的
        xml_file.write('    <progress>1</progress>\n')
        xml_file.write('</item>')
        line = line + 1
# for line in range(len(lines)-1):
#     word, mean = get_content(lines[line])
#     xml_file.write('<item>')
#     xml_file.write('    <word>' + word.strip('\n') + '</word>\n')
#     xml_file.write('    <trans>' + '<![CDATA[' + mean.strip('\n') + ']]>' +  '</trans>\n')
#     xml_file.write('    <tags>reading</tags>\n') #reading是你单词本的名字，你可以改成自己的
#     xml_file.write('    <progress>1</progress>\n')
#     xml_file.write('</item>')

xml_file.write('</wordbook>')
