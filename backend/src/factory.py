from src.extractors.pdfplumber_extractor import PDFPlumberExtractor
from src.extractors.pymupdf_extractor import PyMuPDFExtractor
# from src.extractors.camelot_extractor import CamelotExtractor
from src.extractors.pypdf2_extractor import PyPDF2Extractor
from src.extractors.tesseract_extractor import TesseractExtractor
from src.extractors.textract_extractor import TextractExtractor
from src.extractors.markitdown_extractor import MarkItDownExtractor
from src.extractors.llamaparse import LlamaParseExtractor
from src.extractors.mathpix_extractor import MathpixExtractor
from src.extractors.openai_vision_extractor import OpenAIVisionExtractor
# from src.extractors.tabula_extractor import TabulaExtractor
# from src.extractors.unstructured_extractor import UnstructuredExtractor
from src.models import PDFExtractorType

# Map enum values → reader classes
READER_MAP = {
    PDFExtractorType.PYMUPDF.value: PyMuPDFExtractor,
    PDFExtractorType.PDFPLUMBER.value: PDFPlumberExtractor,
    # PDFExtractorType.CAMELOT.value: CamelotExtractor,
    PDFExtractorType.PYPDF2.value: PyPDF2Extractor,
    PDFExtractorType.TESSERACT.value: TesseractExtractor,
    PDFExtractorType.TEXTRACT.value: TextractExtractor,
    PDFExtractorType.MARKITDOWN.value: MarkItDownExtractor,
    PDFExtractorType.LLAMAPARSE.value: LlamaParseExtractor,
    PDFExtractorType.MATHPIX.value: MathpixExtractor,
    PDFExtractorType.OPENAI_GPT4O_MINI.value: lambda: OpenAIVisionExtractor("gpt-4o-mini"),
    PDFExtractorType.OPENAI_GPT4O.value: lambda: OpenAIVisionExtractor("gpt-4o"),
    PDFExtractorType.OPENAI_GPT4_TURBO.value: lambda: OpenAIVisionExtractor("gpt-4-turbo"),
    # PDFExtractorType.TABULA.value: TabulaExtractor,
    # PDFExtractorType.UNSTRUCTURED.value: UnstructuredExtractor,
}


def get_reader(extractor_type: str):
    """
    Factory method to return an initialized reader
    based on extractor_type (string/enum value).
    """
    if extractor_type not in READER_MAP:
        raise ValueError(f"Unknown extractor type: {extractor_type}")

    return READER_MAP[extractor_type]()
