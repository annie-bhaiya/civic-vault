import os
import base64
import flet as ft
from sqlmodel import Session, select
from app.db.session import init_db, engine, get_db
from app.models.document import Folder, DocumentMetadata
from app.services.vault import VaultService
from app.services.editor import DocumentEditorService

# --- DB INIT ---
def seed_default_folders():
    with Session(engine) as db:
        default_folders = [
            ("Vault Source (Immutable)", True),
            ("Processed & Exported", False),
            ("Identity & KYC", False)
        ]
        for name, is_immutable in default_folders:
            folder = db.exec(select(Folder).where(Folder.name == name)).first()
            if not folder:
                db.add(Folder(name=name, is_immutable=is_immutable))
        db.commit()

init_db()
seed_default_folders()

# --- PRESETS ---
PORTAL_PRESETS = [
    {"label": "Passport Photo (100KB)", "type": "image", "format": "JPEG", "maxKb": 100, "w": 413, "h": 531},
    {"label": "Digital Signature (20KB)", "type": "image", "format": "JPEG", "maxKb": 20, "w": 140, "h": 60},
    {"label": "Govt Portal (200KB)", "type": "image", "format": "JPEG", "maxKb": 200, "w": "", "h": ""},
    {"label": "Identity KYC (500KB)", "type": "pdf", "maxKb": 500, "mode": "standard"},
    {"label": "Standard Cert (1MB)", "type": "pdf", "maxKb": 1000, "mode": "standard"},
    {"label": "Extreme Compress (150KB)", "type": "pdf", "maxKb": 150, "mode": "extreme"}
]

def main(page: ft.Page):
    page.title = "Civic Vault - Smart Engine"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0

    db = next(get_db())
    
    def get_folders():
        return db.exec(select(Folder)).all()

    state = {
        "current_folder_id": get_folders()[0].id if get_folders() else None
    }

    main_view = ft.Container(expand=True)
    page.add(main_view)

    # =========================================================
    # FILE PICKER: Fully Synchronous Binding
    # =========================================================
    def on_file_picked(e: ft.FilePickerResultEvent):
        if e.files and state["current_folder_id"]:
            for f in e.files:
                file_path = getattr(f, "path", None)
                if file_path: 
                    with open(file_path, "rb") as file_data:
                        raw_bytes = file_data.read()
                        VaultService.save_bytes(
                            db=db, file_bytes=raw_bytes, original_filename=f.name,
                            content_type="application/pdf" if f.name.lower().endswith(".pdf") else "image/jpeg",
                            title=f.name, folder_id=state["current_folder_id"]
                        )
            show_dashboard() 
            page.snack_bar = ft.SnackBar(ft.Text(f"Successfully encrypted {len(e.files)} files!"))
            page.snack_bar.open = True
            page.update()

    file_picker = ft.FilePicker()
    file_picker.on_result = on_file_picked
    page.overlay.append(file_picker)
    page.update() 

    def trigger_upload(e):
        file_picker.pick_files(allow_multiple=True)

    # ==========================================
    # FOLDER CRUD: Create New Folder Dialog
    # ==========================================
    def open_create_folder_dialog(e):
        name_input = ft.TextField(label="Folder Name", autofocus=True)

        def create_folder(ev):
            if name_input.value:
                new_folder = Folder(name=name_input.value, is_immutable=False)
                db.add(new_folder)
                db.commit()
                state["current_folder_id"] = new_folder.id
                dialog.open = False
                show_dashboard()

        dialog = ft.AlertDialog(
            title=ft.Text("Create New Vault Folder"),
            content=name_input,
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: setattr(dialog, 'open', False) or page.update()),
                ft.FilledButton("Create", on_click=create_folder)
            ]
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    # ==========================================
    # FILE CRUD: Delete & Move Handlers
    # ==========================================
    def delete_document(doc):
        try:
            # Safely delete the encrypted file from disk using encrypted_file_path
            if doc.encrypted_file_path and os.path.exists(doc.encrypted_file_path):
                os.remove(doc.encrypted_file_path)
            
            db.delete(doc)
            db.commit()
            
            show_dashboard()
            page.snack_bar = ft.SnackBar(ft.Text(f"Deleted '{doc.title}' permanently."))
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Failed to delete: {ex}"))
            page.snack_bar.open = True
            page.update()

    def move_document_dialog(doc):
        folders = get_folders()
        target_dropdown = ft.Dropdown(
            label="Destination Folder",
            options=[ft.dropdown.Option(str(f.id), f.name) for f in folders if f.id != state["current_folder_id"]]
        )

        def confirm_move(ev):
            if target_dropdown.value:
                doc.folder_id = int(target_dropdown.value)
                db.add(doc)
                db.commit()
                dialog.open = False
                show_dashboard()
                page.snack_bar = ft.SnackBar(ft.Text(f"Moved '{doc.title}' successfully."))
                page.snack_bar.open = True
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Text(f"Move '{doc.title}'"),
            content=target_dropdown,
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: setattr(dialog, 'open', False) or page.update()),
                ft.FilledButton("Move", on_click=confirm_move)
            ]
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    # ==========================================
    # VIEW 1: THE DASHBOARD
    # ==========================================
    def show_dashboard():
        folders = get_folders()
        docs_grid = ft.GridView(expand=1, runs_count=5, max_extent=220, child_aspect_ratio=0.85, spacing=15, run_spacing=15)
        
        if state["current_folder_id"]:
            docs = db.exec(select(DocumentMetadata).where(DocumentMetadata.folder_id == state["current_folder_id"])).all()
            for doc in docs:
                icon = ft.Icons.IMAGE if doc.content_type.startswith("image") else ft.Icons.PICTURE_AS_PDF
                color = ft.Colors.BLUE if doc.content_type.startswith("image") else ft.Colors.RED
                
                card = ft.Card(
                    elevation=2,
                    content=ft.Container(
                        padding=15,
                        content=ft.Column([
                            ft.Icon(icon, size=40, color=color),
                            ft.Text(doc.title, weight=ft.FontWeight.BOLD, size=14, no_wrap=True, max_lines=1),
                            ft.Text(f"{doc.file_size_bytes // 1024} KB", size=12, color=ft.Colors.GREY),
                            ft.Divider(height=10),
                            ft.OutlinedButton("Open Engine", icon=ft.Icons.SETTINGS, on_click=lambda e, d=doc: show_editor(d), height=30),
                            ft.Row([
                                ft.IconButton(icon=ft.Icons.DRAG_HANDLE, tooltip="Move File", icon_size=18, on_click=lambda e, d=doc: move_document_dialog(d)),
                                ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, tooltip="Delete File", icon_size=18, icon_color=ft.Colors.RED, on_click=lambda e, d=doc: delete_document(d))
                            ], alignment=ft.MainAxisAlignment.SPACE_EVENLY)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                    )
                )
                docs_grid.controls.append(card)

        def on_nav_change(e):
            state["current_folder_id"] = folders[e.control.selected_index].id
            show_dashboard()

        selected_idx = next((i for i, f in enumerate(folders) if f.id == state["current_folder_id"]), 0)
        nav_rail = ft.NavigationRail(
            expand=True,
            selected_index=selected_idx if selected_idx < len(folders) else 0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=200,
            destinations=[ft.NavigationRailDestination(icon=ft.Icons.FOLDER_OUTLINED, selected_icon=ft.Icons.FOLDER, label=f.name) for f in folders],
            on_change=on_nav_change,
        )

        sidebar_content = ft.Column([
            nav_rail,
            ft.Divider(height=1),
            ft.Container(
                padding=10,
                content=ft.OutlinedButton("New Folder", icon=ft.Icons.CREATE_NEW_FOLDER, on_click=open_create_folder_dialog)
            )
        ], spacing=0)

        main_view.content = ft.Row([
            sidebar_content,
            ft.VerticalDivider(width=1),
            ft.Container(
                expand=True, padding=20,
                content=ft.Column([
                    ft.Row([
                        ft.Text("Civic Vault Dashboard", size=28, weight=ft.FontWeight.BOLD),
                        ft.FilledButton("Upload Secure File", icon=ft.Icons.UPLOAD, on_click=trigger_upload)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(),
                    docs_grid
                ])
            )
        ], expand=True)
        page.update()

    # ==========================================
    # VIEW 2: THE SMART EDITOR
    # ==========================================
    def show_editor(doc: DocumentMetadata):
        raw_bytes, metadata = VaultService.retrieve_document(db=db, doc_id=doc.id)
        is_image = metadata.content_type.startswith("image")
        
        target_kb_input = ft.TextField(label="Max KB Limit", value="")
        fmt_dropdown = ft.Dropdown(label="Format", options=[ft.dropdown.Option("JPEG"), ft.dropdown.Option("PNG"), ft.dropdown.Option("PDF")], value="JPEG")
        w_input = ft.TextField(label="Width (px)", value="", expand=1)
        h_input = ft.TextField(label="Height (px)", value="", expand=1)
        
        pdf_mode_dropdown = ft.Dropdown(label="Compression Level", options=[ft.dropdown.Option("standard", "Standard"), ft.dropdown.Option("extreme", "Extreme")], value="standard")
        unlock_pw_input = ft.TextField(label="Unlock Password (if locked)", password=True, can_reveal_password=True)
        lock_pw_input = ft.TextField(label="New PDF Password", password=True, can_reveal_password=True)
        
        watermark_input = ft.TextField(label="KYC Watermark Text", value="PROVIDED SOLELY FOR KYC PURPOSES")
        ocr_display = ft.TextField(label="Extracted Text (OCR)", multiline=True, read_only=True, min_lines=4, max_lines=4)
        
        name_input = ft.TextField(label="Verified Name", value=doc.extracted_name or "")
        dob_input = ft.TextField(label="Verified DOB (YYYY-MM-DD)", value=doc.extracted_dob or "")
        bio_input = ft.TextField(label="Last Biometric Update", value=doc.biometric_update_date or "")

        def show_msg(msg):
            page.snack_bar = ft.SnackBar(ft.Text(msg))
            page.snack_bar.open = True
            page.update()

        def finish_processing(new_bytes, new_mime, ext, tag):
            base = os.path.splitext(metadata.original_filename)[0]
            proc_folder = db.exec(select(Folder).where(Folder.name == "Processed & Exported")).first()
            VaultService.save_bytes(
                db=db, file_bytes=new_bytes, original_filename=f"{base}_{tag}{ext}",
                content_type=new_mime, title=f"{metadata.title} ({tag})", folder_id=proc_folder.id if proc_folder else doc.folder_id
            )
            show_msg("Processing Complete! Saved to Processed Folder.")
            show_dashboard()

        def apply_preset(p):
            target_kb_input.value = str(p["maxKb"])
            if is_image and p["type"] == "image":
                fmt_dropdown.value = p["format"]
                w_input.value = str(p["w"]) if p["w"] else ""
                h_input.value = str(p["h"]) if p["h"] else ""
            elif not is_image and p["type"] == "pdf":
                pdf_mode_dropdown.value = p["mode"]
            page.update()

        def do_image_edit(e):
            class DummyParams:
                target_format = fmt_dropdown.value
                quality = 85
                target_size_kb = int(target_kb_input.value) if target_kb_input.value else None
                crop_x = crop_y = crop_width = crop_height = None
                resize_width = int(w_input.value) if w_input.value else None
                resize_height = int(h_input.value) if h_input.value else None
            try:
                b, m, ext = DocumentEditorService.process_image(raw_bytes, DummyParams())
                finish_processing(b, m, ext, "edited")
            except Exception as ex: show_msg(str(ex))

        def do_pdf_compress(e):
            try:
                kb = int(target_kb_input.value) if target_kb_input.value else None
                b, m, ext = DocumentEditorService.compress_pdf(raw_bytes, pdf_mode_dropdown.value, unlock_pw_input.value, kb)
                finish_processing(b, m, ext, "compressed")
            except Exception as ex: show_msg(str(ex))

        def do_pdf_lock(e):
            if not lock_pw_input.value: return show_msg("Enter a password to lock!")
            try:
                b, m, ext = DocumentEditorService.lock_pdf(raw_bytes, lock_pw_input.value)
                finish_processing(b, m, ext, "locked")
            except Exception as ex: show_msg(str(ex))

        def do_watermark(e):
            try:
                b, m, ext = DocumentEditorService.apply_watermark(raw_bytes, metadata.content_type, watermark_input.value, unlock_pw_input.value)
                finish_processing(b, m, ext, "KYC_stamped")
            except Exception as ex: show_msg(str(ex))

        def do_ocr(e):
            ocr_display.value = "Scanning natively... Please wait..."
            page.update()
            try:
                txt = DocumentEditorService.extract_text(raw_bytes, metadata.content_type, unlock_pw_input.value)
                ocr_display.value = txt if txt else "No text found."
            except Exception as ex: ocr_display.value = f"OCR Error: {ex}"
            page.update()

        def save_audit_data(e):
            doc.extracted_name = name_input.value
            doc.extracted_dob = dob_input.value
            doc.biometric_update_date = bio_input.value
            db.add(doc)
            db.commit()
            show_msg("Intelligence Data Saved to DB!")

        b64_str = base64.b64encode(raw_bytes).decode("utf-8")
        
        preview_panel = ft.Column([
            ft.Text("Document Preview", weight=ft.FontWeight.BOLD, size=18),
            ft.Image(src=b64_str, fit="contain", height=300) 
            if is_image else ft.Icon(ft.Icons.PICTURE_AS_PDF, size=100, color=ft.Colors.RED),
            ft.Divider(),
            ft.Row([ft.Text("Offline OCR Engine", weight=ft.FontWeight.BOLD), ft.FilledButton("Extract Text", on_click=do_ocr, height=30)]),
            ocr_display,
            ft.Text("Verify & Feed Engine", weight=ft.FontWeight.BOLD),
            name_input, dob_input, bio_input,
            ft.FilledButton("Save to Database", on_click=save_audit_data, width=400)
        ], expand=1, spacing=10)

        preset_buttons = [ft.OutlinedButton(p["label"], on_click=lambda e, pr=p: apply_preset(pr), height=35) 
                          for p in PORTAL_PRESETS if (p["type"] == "image") == is_image]
        
        tools = [
            ft.Text("1-Click Presets", weight=ft.FontWeight.BOLD, size=18),
            ft.Row(preset_buttons, wrap=True),
            ft.Divider(),
            ft.Text("Manual Constraints", weight=ft.FontWeight.BOLD),
            target_kb_input,
        ]

        if is_image:
            tools.extend([
                ft.Row([w_input, h_input]), fmt_dropdown,
                ft.FilledButton("Process & Save Image", icon=ft.Icons.SAVE, on_click=do_image_edit)
            ])
        else:
            tools.extend([
                pdf_mode_dropdown, unlock_pw_input,
                ft.FilledButton("Compress PDF", icon=ft.Icons.COMPRESS, on_click=do_pdf_compress),
                ft.Divider(),
                lock_pw_input,
                ft.FilledTonalButton("Encrypt PDF", icon=ft.Icons.LOCK, on_click=do_pdf_lock)
            ])

        tools.extend([
            ft.Divider(),
            ft.Text("Phase 5: KYC Watermark", weight=ft.FontWeight.BOLD),
            ft.FilledButton("Apply Permanent Stamp", icon=ft.Icons.SECURITY, on_click=do_watermark)
        ])

        tool_panel = ft.Column(tools, expand=1, scroll="auto", spacing=15)

        main_view.content = ft.Container(
            padding=20,
            expand=True,
            content=ft.Column([
                ft.Row([
                    ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _: show_dashboard()),
                    ft.Text(f"Smart Engine: {doc.title}", size=24, weight=ft.FontWeight.BOLD)
                ]),
                ft.Divider(),
                ft.Row([
                    ft.Container(content=preview_panel, expand=1, padding=10),
                    ft.VerticalDivider(width=1),
                    ft.Container(content=tool_panel, expand=1, padding=10)
                ], expand=True)
            ], expand=True)
        )
        page.update()

    show_dashboard()

ft.run(main)