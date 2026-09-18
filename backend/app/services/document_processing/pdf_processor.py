import PyPDF2
import io
from typing import Optional
from pathlib import Path


async def process_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text content
        
    Raises:
        Exception: If PDF processing fails
    """
    try:
        extracted_text = []
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Extract text from each page
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text() or ""
                
                if text.strip():
                    extracted_text.append(text)
        
        # Join all pages with double newline
        full_text = "\n\n".join(extracted_text)
        
        if not full_text.strip():
            raise ValueError("No text could be extracted from the PDF")
        
        return full_text
        
    except Exception as e:
        raise Exception(f"PDF processing failed: {str(e)}")


async def get_pdf_metadata(file_path: str) -> dict:
    """
    Extract metadata from a PDF file
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Dictionary containing PDF metadata
    """
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            metadata = {
                "page_count": len(pdf_reader.pages),
                "title": pdf_reader.metadata.get('/Title', None) if pdf_reader.metadata else None,
                "author": pdf_reader.metadata.get('/Author', None) if pdf_reader.metadata else None,
                "subject": pdf_reader.metadata.get('/Subject', None) if pdf_reader.metadata else None,
            }
            
            return metadata
            
    except Exception as e:
        return {"page_count": 0, "error": str(e)}
