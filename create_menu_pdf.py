from fpdf import FPDF
import os

def create_menu_pdf():
    pdf = FPDF()
    pdf.add_page()
    
    # Set font for Vietnamese characters
    pdf.add_font('DejaVu', '', 'DejaVuSansCondensed.ttf', uni=True)
    pdf.set_font('DejaVu', '', 12)
    
    # Read the text file
    text_path = 'hoadeptrai/static/docs/menu.txt'
    pdf_path = 'hoadeptrai/static/docs/menu.pdf'
    
    with open(text_path, 'r', encoding='utf-8') as file:
        for line in file:
            pdf.cell(0, 10, line.strip(), ln=True)
    
    # Save the PDF
    pdf.output(pdf_path)

if __name__ == '__main__':
    create_menu_pdf()
