import os
from typing import Any, BinaryIO
import cv2
from markitdown._base_converter import DocumentConverter, DocumentConverterResult, StreamInfo
import numpy as np
from PIL import Image
import pdf2image
import pytesseract

class OCRPDFConverter(DocumentConverter):
    def __init__(self, ocr_langs="eng+equ", dpi=400):
        self.ocr_langs = ocr_langs
        self.dpi = dpi
        self._validate_environment()

    def _validate_environment(self):
        """Verify all required binaries are installed"""
        try:
            pytesseract.get_tesseract_version()
            from shutil import which
            if not which("pdftoppm"):
                raise RuntimeError("poppler-utils not installed")
        except Exception as e:
            raise RuntimeError(f"Dependency check failed: {str(e)}")

    def _preprocess_image(self, img, page_number):
        """Enhanced image preprocessing pipeline with debugging."""
        try:
            print(f"🔄 Preprocessing image for page {page_number}...")
            # Convert to OpenCV format
            img = np.array(img)

            # Resize image to improve OCR accuracy
            height, width = img.shape[:2]
            scale_factor = 2  # Scale up by 2x
            img = cv2.resize(img, (width * scale_factor, height * scale_factor), interpolation=cv2.INTER_CUBIC)

            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

            # Apply adaptive thresholding for better OCR
            adaptive_thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )

            # Save intermediate image for debugging
            debug_path = f"debug_page_{page_number}_preprocessed.jpg"
            cv2.imwrite(debug_path, adaptive_thresh)
            print(f"🔍 Saved preprocessed image for page {page_number}: {debug_path}")

            return Image.fromarray(adaptive_thresh)
        except Exception as e:
            print(f"❌ Preprocessing failed for page {page_number}: {str(e)}")
            return img  # Return the original image as a fallback

    def convert(self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any) -> DocumentConverterResult:
        debug_dir = "/home/ttejaswi/markitdown_rag_poc/debug_images"
        os.makedirs(debug_dir, exist_ok=True)
        try:
            print("🔄 Reading PDF file...")
            pdf_bytes = file_stream.read()
            if len(pdf_bytes) < 5000:
                raise ValueError("PDF file too small (possibly corrupt)")

            # Convert PDF to images
            print("🔄 Converting PDF to images...")
            images = pdf2image.convert_from_bytes(
                pdf_bytes,
                dpi=self.dpi,
                grayscale=True,
                thread_count=4,
                poppler_path="/usr/bin"
            )
            if not images:
                raise ValueError("PDF rendered 0 pages (password protected?)")
            print(f"✅ PDF converted to {len(images)} image(s).")

            page_texts = []
            for i, img in enumerate(images):
                print(f"🔄 Processing page {i + 1}...")
                # Save raw extracted image for debugging
                raw_image_path = os.path.join(debug_dir, f"raw_page_{i+1}.jpg")
                img.save(raw_image_path)
                print(f"🔍 Saved raw image for page {i+1}: {raw_image_path}")

                # Preprocess the image
                preprocessed_img = self._preprocess_image(img, i + 1)

                # Apply OCR to the preprocessed image
                print(f"🔄 Applying OCR to page {i + 1}...")
                text = pytesseract.image_to_string(preprocessed_img, lang=self.ocr_langs).strip()
                if text:
                    page_texts.append(f"# Page {i+1}\n\n{text}")
                    print(f"✅ Page {i+1} OCR success: {len(text)} chars")
                else:
                    print(f"⚠️ Page {i+1} OCR returned empty text")
                    page_texts.append(f"# Page {i+1}\n\n⚠️ No text extracted from this page.")

            if not page_texts:
                print("❌ OCR produced empty text. Returning a fallback message.")
                return DocumentConverterResult(
                    title=stream_info.filename or "Scanned PDF",
                    markdown="❌ OCR failed to extract text. The PDF may be blank or unreadable."
                )

            # Combine text from all pages
            combined_text = "\n\n---\n\n".join(page_texts)
            print(f"✅ Combined OCR text length: {len(combined_text)}")
            return DocumentConverterResult(
                title=stream_info.filename,
                markdown=combined_text,
                metadata={
                    "ocr_stats": {
                        "success_pages": len([t for t in page_texts if "No text extracted" not in t]),
                        "total_pages": len(images)
                    }
                }
            )
        except Exception as e:
            print(f"❌ OCR processing failed: {str(e)}")
            raise RuntimeError(f"OCR processing failed: {str(e)}")