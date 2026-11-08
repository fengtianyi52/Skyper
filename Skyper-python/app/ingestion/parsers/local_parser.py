"""Parse common text documents locally; use MinerU only when OCR is needed."""
import asyncio
import io

from langchain_core.documents import Document

from app.ingestion.errors import IngestionError
from app.ingestion.parsers.base import DocumentParser


class DocxParser(DocumentParser):
    async def parse(self, data: bytes, file_name: str) -> list[Document]:
        documents = await asyncio.to_thread(self._parse, data, file_name)
        if documents:
            return documents
        from app.ingestion.parsers.mineru_parser import MineruParser
        return await MineruParser().parse(data, file_name)

    @staticmethod
    def _parse(data: bytes, file_name: str) -> list[Document]:
        from docx import Document as WordDocument
        from docx.oxml.ns import qn
        from lxml.etree import iterwalk
        try:
            word = WordDocument(io.BytesIO(data))
            # Word's Paragraph.text omits DrawingML text, text boxes and some
            # content controls. Traverse text nodes in document order instead.
            parts = []
            text_tags = {qn('w:t'), qn('a:t')}
            paragraph_tags = {qn('w:p'), qn('a:p'), qn('w:tr')}
            for event, element in iterwalk(word.element.body, events=('start', 'end')):
                if event == 'start' and element.tag in text_tags:
                    parts.append(element.text or '')
                elif event == 'end' and element.tag in paragraph_tags:
                    parts.append('\n')
                elif event == 'end' and element.tag == qn('w:tc'):
                    parts.append(' | ')
                elif event == 'start' and element.tag in {qn('w:br'), qn('a:br')}:
                    parts.append('\n')
                elif event == 'start' and element.tag == qn('w:tab'):
                    parts.append('\t')
            text = ''.join(parts).strip()
        except Exception as exc:
            raise IngestionError('Word 解析失败：文件损坏、加密或并非真正的 DOCX。请用 Word 另存为 .docx 后重新上传。') from exc
        return [Document(page_content=text, metadata={'source': file_name, 'parser': 'local-docx'})] if text else []


class PdfParser(DocumentParser):
    async def parse(self, data: bytes, file_name: str) -> list[Document]:
        documents, needs_ocr = await asyncio.to_thread(self._parse, data, file_name)
        if needs_ocr:
            # Do not silently drop scanned pages from a mixed PDF.
            from app.ingestion.parsers.mineru_parser import MineruParser
            return await MineruParser().parse(data, file_name)
        return documents

    @staticmethod
    def _parse(data: bytes, file_name: str) -> tuple[list[Document], bool]:
        import pdfplumber
        try:
            documents = []
            needs_ocr = False
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                for index, page in enumerate(pdf.pages):
                    text = (page.extract_text() or '').strip()
                    if text:
                        documents.append(Document(page_content=text, metadata={'source': file_name, 'page': index + 1, 'parser': 'local-pdf'}))
                    elif page.images:
                        needs_ocr = True
            return documents, needs_ocr or not documents
        except Exception as exc:
            raise IngestionError('PDF 解析失败：文件损坏或需要密码。请导出为未加密 PDF 后重新上传。') from exc
