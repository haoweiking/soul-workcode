from PyPDF2 import PdfReader, PdfWriter
import os


def add_qr_code_to_pdf(image_pdf_path, pdf_path, write_path):
    pdf_reader = PdfReader(pdf_path)

    '''
    first page to writer
    QR code to writer
    reader remaining pages to writer
    # writer insert_page 为倒序
    '''
    pdf_write = PdfWriter()

    # reader remaining pages to writer
    for index in range(len(pdf_reader.pages) - 1, 0, -1):
        pdf_write.insert_page(pdf_reader.pages[index])

    # QR code to writer
    qr_reader = PdfReader(image_pdf_path)
    pdf_write.insert_page(qr_reader.pages[0])

    # first page to writer
    pdf_write.insert_page(pdf_reader.pages[0])

    with open(write_path, "wb") as output_stream:
        pdf_write.write(output_stream)


if __name__ == "__main__":
    current_path = os.getcwd()
    qr_pdf_path = f"{current_path}/cover.pdf"

    for pdf_file in os.listdir("."):
        if pdf_file.endswith(".pdf"):
            pdf_path = os.path.join(".", pdf_file)
            if pdf_path.endswith("cover.pdf"):
                continue
            output_path = f"output_{pdf_file}"
            add_qr_code_to_pdf(qr_pdf_path, pdf_path, output_path)
            print(f"Image added to {pdf_file} and saved as {output_path}")
    