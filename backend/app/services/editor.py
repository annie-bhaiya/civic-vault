import io
from PIL import Image, ImageEnhance, ImageDraw, ImageFont # <--- Added ImageEnhance
import fitz  # PyMuPDF
import pytesseract


class DocumentEditorService:
    @staticmethod
    def strip_exif(image: Image.Image) -> Image.Image:
        """Silently strips all hidden metadata/GPS for privacy."""
        data = list(image.getdata())
        image_without_exif = Image.new(image.mode, image.size)
        image_without_exif.putdata(data)
        return image_without_exif

    @staticmethod
    def process_image(raw_bytes: bytes, params) -> tuple[bytes, str, str]:
        original_size = len(raw_bytes)
        image = Image.open(io.BytesIO(raw_bytes))
        image = DocumentEditorService.strip_exif(image)
        
        # Determine if the user is changing the file type
        original_format = (image.format or "JPEG").upper()
        target_format = (params.target_format or original_format).upper()
        if target_format == "JPG":
            target_format = "JPEG"
        
        is_format_change = target_format != original_format
        
        if target_format in ["JPEG", "PDF"] and image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
            
        if all(v is not None for v in [params.crop_x, params.crop_y, params.crop_width, params.crop_height]):
            box = (params.crop_x, params.crop_y, params.crop_x + params.crop_width, params.crop_y + params.crop_height)
            image = image.crop(box)
            
        if params.resize_width and params.resize_height:
            image = image.resize((params.resize_width, params.resize_height), Image.Resampling.LANCZOS)
            
        out_buffer = io.BytesIO()
        
        if target_format == "PDF":
            image.save(out_buffer, format="PDF", resolution=100.0, save_all=True)
            final_bytes = out_buffer.getvalue()
            
            # Validation 1: Check if PDF conversion missed the KB target
            if params.target_size_kb and len(final_bytes) > (params.target_size_kb * 1024):
                raise ValueError(f"Target size of {params.target_size_kb}KB is mathematically impossible for this document.")
                
            return final_bytes, "application/pdf", ".pdf"
        else:
            current_quality = params.quality
            while True:
                out_buffer = io.BytesIO()
                image.save(out_buffer, format=target_format, quality=current_quality, optimize=True)
                final_bytes = out_buffer.getvalue()
                
                if not params.target_size_kb:
                    break
                if len(final_bytes) <= (params.target_size_kb * 1024) or current_quality <= 10:
                    break
                current_quality -= 15
                
            # Validation 2: Target missed even at lowest quality
            if params.target_size_kb and len(final_bytes) > (params.target_size_kb * 1024):
                raise ValueError(f"Target size of {params.target_size_kb}KB is mathematically impossible without destroying the image.")
                
            # Validation 3: Prevent bloat if standard compression increases size
            if not params.target_size_kb and not is_format_change and len(final_bytes) >= original_size:
                raise ValueError("This image is already maximally compressed. Generating a new file would only increase its size.")
                
            return final_bytes, f"image/{target_format.lower()}", f".{target_format.lower()}"

    @staticmethod
    def compress_pdf(raw_bytes: bytes, mode: str = "standard", password: str = None, target_size_kb: int = None) -> tuple[bytes, str, str]:
        original_size = len(raw_bytes)
        pdf_document = fitz.open(stream=raw_bytes, filetype="pdf")
        
        if pdf_document.is_encrypted:
            if not password:
                if not pdf_document.authenticate(""):
                    raise ValueError("This PDF is locked. An unlock password is required.")
            else:
                if not pdf_document.authenticate(password):
                    raise ValueError("Incorrect unlock password provided.")

        save_kwargs = {"garbage": 4, "deflate": True}
        if password:
            save_kwargs["encryption"] = fitz.PDF_ENCRYPT_AES_256
            save_kwargs["user_pw"] = password
            save_kwargs["owner_pw"] = password

        if mode == "extreme":
            current_dpi = 100
            current_img_quality = 35
            
            while True:
                new_pdf = fitz.open()
                for page_num in range(len(pdf_document)):
                    page = pdf_document.load_page(page_num)
                    pix = page.get_pixmap(dpi=current_dpi, alpha=False, colorspace=fitz.csGRAY)
                    img = Image.frombytes("L", [pix.width, pix.height], pix.samples)
                    img_buffer = io.BytesIO()
                    img.save(img_buffer, format="JPEG", quality=current_img_quality, optimize=True)
                    new_page = new_pdf.new_page(width=page.rect.width, height=page.rect.height)
                    new_page.insert_image(page.rect, stream=img_buffer.getvalue())
                    
                out_buffer = io.BytesIO()
                new_pdf.save(out_buffer, **save_kwargs)
                new_pdf.close()
                final_bytes = out_buffer.getvalue()
                
                if not target_size_kb:
                    break
                if len(final_bytes) <= (target_size_kb * 1024) or current_dpi <= 50:
                    break
                    
                current_dpi -= 25
                current_img_quality -= 5
                
            # Validation 1: Extreme mode failed to hit KB target
            if target_size_kb and len(final_bytes) > (target_size_kb * 1024):
                raise ValueError(f"Target size of {target_size_kb}KB is mathematically impossible for this PDF.")
                
            # Validation 2: Extreme mode expanded the file
            if not target_size_kb and len(final_bytes) >= original_size:
                # Try falling back to lossless standard mode
                out_buffer = io.BytesIO()
                pdf_document.save(out_buffer, **save_kwargs)
                final_bytes = out_buffer.getvalue()
                if len(final_bytes) >= original_size:
                    raise ValueError("This PDF is already maximally compressed. No further space can be saved.")
        else:
            out_buffer = io.BytesIO()
            pdf_document.save(out_buffer, **save_kwargs)
            final_bytes = out_buffer.getvalue()
            
            # Validation 3: Standard mode failed to hit KB target
            if target_size_kb and len(final_bytes) > (target_size_kb * 1024):
                raise ValueError(f"Target size of {target_size_kb}KB cannot be met in Standard Mode. Try Extreme Scan instead.")
                
            # Validation 4: Standard mode expanded the file
            if not target_size_kb and len(final_bytes) >= original_size:
                raise ValueError("This PDF is already maximally compressed. No further space can be saved.")
            
        pdf_document.close()
        return final_bytes, "application/pdf", ".pdf"

    @staticmethod
    def lock_pdf(raw_bytes: bytes, password: str) -> tuple[bytes, str, str]:
        pdf_document = fitz.open(stream=raw_bytes, filetype="pdf")
        if pdf_document.is_encrypted:
            pdf_document.authenticate("")
        out_buffer = io.BytesIO()
        pdf_document.save(out_buffer, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=password)
        pdf_document.close()
        return out_buffer.getvalue(), "application/pdf", ".pdf"

    @staticmethod
    def extract_text(raw_bytes: bytes, content_type: str, password: str = None) -> str:
        if content_type == "application/pdf":
            doc = fitz.open(stream=raw_bytes, filetype="pdf")
            if doc.is_encrypted:
                doc.authenticate(password or "")
            page = doc.load_page(0)
            # Increased DPI from 150 to 300 specifically for OCR accuracy
            pix = page.get_pixmap(dpi=300, alpha=False, colorspace=fitz.csGRAY)
            img = Image.frombytes("L", [pix.width, pix.height], pix.samples)
            doc.close()
        else:
            img = Image.open(io.BytesIO(raw_bytes))
            # 1. Convert image to pure Grayscale
            if img.mode != 'L':
                img = img.convert('L')
            
            # 2. Aggressively boost the contrast to separate text from background noise
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.5) # 2.5x contrast

        # 3. Apply custom Tesseract configuration:
        # --oem 3 : Use Default OCR Engine Mode
        # --psm 11: "Sparse text" - forces it to look for scattered words (perfect for ID cards)
        custom_config = r'--oem 3 --psm 11'
        text = pytesseract.image_to_string(img, config=custom_config)
        
        return text.strip()

    @staticmethod
    def apply_watermark(raw_bytes: bytes, content_type: str, text: str, password: str = None) -> tuple[bytes, str, str]:
        """Applies a permanent anti-misuse watermark to Images or PDFs."""
        
        if content_type == "application/pdf":
            pdf = fitz.open(stream=raw_bytes, filetype="pdf")
            if pdf.is_encrypted:
                if not password or not pdf.authenticate(password):
                    raise ValueError("Incorrect unlock password provided for PDF.")
            
            # Stamp every page diagonally
            for page in pdf:
                # Red text, size 25, angled at 45 degrees
                p1 = fitz.Point(30, page.rect.height / 2)
                page.insert_text(p1, text, fontsize=25, color=(0.8, 0.1, 0.1), rotate=-45)
                
            out_buffer = io.BytesIO()
            save_kwargs = {"garbage": 4, "deflate": True}
            if password:
                save_kwargs.update({"encryption": fitz.PDF_ENCRYPT_AES_256, "user_pw": password, "owner_pw": password})
            pdf.save(out_buffer, **save_kwargs)
            pdf.close()
            return out_buffer.getvalue(), "application/pdf", ".pdf"
            
        else:
            image = Image.open(io.BytesIO(raw_bytes))
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
                
            txt_layer = Image.new('RGBA', image.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)
            font = ImageFont.load_default()
            
            # Draw a dark, semi-transparent security banner across the bottom
            width, height = image.size
            banner_height = 40
            draw.rectangle(((0, height - banner_height), (width, height)), fill=(0, 0, 0, 180))
            draw.text((10, height - 25), text, fill=(255, 100, 100, 255), font=font)
            
            watermarked = Image.alpha_composite(image, txt_layer).convert('RGB')
            out_buffer = io.BytesIO()
            watermarked.save(out_buffer, format="JPEG", quality=90)
            return out_buffer.getvalue(), "image/jpeg", ".jpeg"