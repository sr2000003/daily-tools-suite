import flet as ft
from pydub import AudioSegment
from PIL import Image, ImageOps, ImageEnhance
from PyPDF2 import PdfMerger
import anthropic
import io
import base64
import os
import math


def read_file(file):
    """Read file in both desktop (path) and web (bytes) mode."""
    if file.path and os.path.exists(file.path):
        with open(file.path, "rb") as f:
            return f.read()
    return None


# ── AUDIO TAB ─────────────────────────────────────────────────────────────────
class AudioTab(ft.Column):
    def __init__(self, page):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO)
        self.page = page
        self.tracks = []
        self.status = ft.Text("Audio Studio: Ready", color=ft.colors.BLUE_200)
        self.file_list = ft.ListView(expand=True, spacing=5)

    def build(self):
        return ft.Column([
            ft.Text("Audio Editor", size=25, weight=ft.FontWeight.BOLD),
            ft.Row([
                ft.ElevatedButton("Add Track", icon=ft.icons.ADD,
                                  on_click=lambda _: self.picker.pick_files(allow_multiple=True)),
                self.status,
            ]),
            ft.Container(self.file_list, bgcolor=ft.colors.WHITE10,
                         border_radius=10, padding=10, height=150),
            ft.Text("Effects"),
            ft.Row([
                ft.TextField(label="Fade In (ms)", value="1000", width=130),
                ft.TextField(label="Fade Out (ms)", value="1000", width=130),
            ]),
            ft.ElevatedButton("Join & Export", icon=ft.icons.SAVE,
                              on_click=self.export_audio, bgcolor=ft.colors.BLUE_800),
        ])

    def export_audio(self, e):
        if not self.tracks:
            return
        combined = self.tracks[0]
        for t in self.tracks[1:]:
            combined = combined.append(t, crossfade=100)
        path = "Combined_Audio.mp3"
        combined.export(path, format="mp3")
        self.page.snack_bar = ft.SnackBar(ft.Text(f"Exported: {path}"))
        self.page.snack_bar.open = True
        self.page.update()


# ── PHOTO TAB ─────────────────────────────────────────────────────────────────
class PhotoTab(ft.Column):
    def __init__(self, page):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO)
        self.page = page
        self.curr_img = None
        self.img_display = ft.Image(width=300, height=300, fit=ft.ImageFit.CONTAIN)

    def build(self):
        return ft.Column([
            ft.Text("Lumina Photo Editor", size=25, weight=ft.FontWeight.BOLD),
            ft.Container(self.img_display, bgcolor=ft.colors.BLACK38, border_radius=10),
            ft.Row([
                ft.IconButton(ft.icons.BRIGHTNESS_6, tooltip="Brighten",
                              on_click=lambda _: self.apply("bright")),
                ft.IconButton(ft.icons.COLOR_LENS, tooltip="Sepia",
                              on_click=lambda _: self.apply("sepia")),
                ft.IconButton(ft.icons.CONTRAST, tooltip="Contrast",
                              on_click=lambda _: self.apply("contrast")),
                ft.IconButton(ft.icons.ROTATE_RIGHT, tooltip="Rotate",
                              on_click=lambda _: self.apply("rotate")),
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.ElevatedButton("Open Photo", icon=ft.icons.IMAGE,
                              on_click=lambda _: self.picker.pick_files(
                                  allowed_extensions=["jpg", "jpeg", "png", "bmp", "gif"])),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    def apply(self, mode):
        if not self.curr_img:
            return
        if mode == "bright":
            self.curr_img = ImageEnhance.Brightness(self.curr_img).enhance(1.2)
        elif mode == "sepia":
            self.curr_img = ImageOps.colorize(
                ImageOps.grayscale(self.curr_img), "#704214", "#C0A080")
        elif mode == "contrast":
            self.curr_img = ImageEnhance.Contrast(self.curr_img).enhance(1.3)
        elif mode == "rotate":
            self.curr_img = self.curr_img.rotate(90, expand=True)
        self._refresh()

    def _refresh(self):
        buf = io.BytesIO()
        img = self.curr_img.convert("RGB")
        img.save(buf, format="PNG")
        self.img_display.src_base64 = base64.b64encode(buf.getvalue()).decode()
        self.page.update()


# ── PDF TAB ───────────────────────────────────────────────────────────────────
class PdfTab(ft.Column):
    def __init__(self, page):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO)
        self.page = page
        self.paths = []
        self.file_list = ft.ListView(spacing=4, height=120)

    def build(self):
        return ft.Column([
            ft.Text("PDF Merger", size=25, weight=ft.FontWeight.BOLD),
            ft.ElevatedButton("Select PDFs", icon=ft.icons.FILE_COPY,
                              on_click=lambda _: self.picker.pick_files(
                                  allow_multiple=True, allowed_extensions=["pdf"])),
            ft.Container(self.file_list, bgcolor=ft.colors.WHITE10,
                         border_radius=8, padding=8, height=130),
            ft.ElevatedButton("Merge & Save", icon=ft.icons.MERGE_TYPE,
                              on_click=self.merge, bgcolor=ft.colors.GREEN_700),
        ])

    def merge(self, e):
        if not self.paths:
            return
        m = PdfMerger()
        for p in self.paths:
            m.append(p)
        out = "Merged.pdf"
        m.write(out)
        self.page.snack_bar = ft.SnackBar(ft.Text(f"Saved: {out}"))
        self.page.snack_bar.open = True
        self.page.update()


# ── CALCULATOR TAB ────────────────────────────────────────────────────────────
class CalcTab(ft.Column):
    def __init__(self, page):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO)
        self.page = page
        self.expr = ""
        self.image_b64 = None
        self.image_mime = "image/jpeg"

        self.display = ft.TextField(
            value="0", read_only=True, text_size=26,
            text_align=ft.TextAlign.RIGHT,
            bgcolor=ft.colors.BLACK54, border_radius=8,
        )
        self.ai_input = ft.TextField(
            label="Type a math question (calculus, algebra, etc.) or upload an image…",
            multiline=True, min_lines=2, max_lines=5, expand=True,
        )
        self.ai_result = ft.Text("", selectable=True, size=14)
        self.img_preview = ft.Image(
            width=220, height=160, fit=ft.ImageFit.CONTAIN, visible=False
        )
        self.solving_indicator = ft.ProgressRing(width=20, height=20, visible=False)

    # ── layout ────────────────────────────────────────────────────────────────
    def build(self):
        btn_grid = [
            ["sin", "cos", "tan", "π",  "e"  ],
            ["log", "ln",  "√",  "x²", "xʸ" ],
            ["(",   ")",   "CE",  "C", "⌫"  ],
            ["7",   "8",   "9",  "÷",  "%"  ],
            ["4",   "5",   "6",  "×",  "1/x"],
            ["1",   "2",   "3",  "-",  "!"  ],
            ["0",   ".",   "±",  "+",  "="  ],
        ]

        rows = []
        for row in btn_grid:
            rows.append(ft.Row([
                ft.ElevatedButton(
                    text=b,
                    expand=True,
                    height=48,
                    on_click=lambda e, b=b: self._btn(b),
                    style=ft.ButtonStyle(
                        bgcolor=(
                            ft.colors.GREEN_700 if b == "=" else
                            ft.colors.ORANGE_700 if b in ["÷", "×", "-", "+"] else
                            ft.colors.RED_700 if b in ["C", "CE", "⌫"] else
                            ft.colors.BLUE_GREY_700
                        )
                    ),
                ) for b in row
            ], spacing=3))

        return ft.Column([
            ft.Text("Scientific Calculator", size=22, weight=ft.FontWeight.BOLD),
            self.display,
            ft.Column(rows, spacing=3),

            ft.Divider(height=20),
            ft.Text("AI Math Solver", size=18, weight=ft.FontWeight.BOLD),
            ft.Text("Solves calculus, algebra, geometry, statistics — type or upload a photo",
                    size=12, color=ft.colors.GREY_400),

            ft.Row([self.ai_input]),
            self.img_preview,
            ft.Row([
                ft.ElevatedButton(
                    "Upload / Camera Photo",
                    icon=ft.icons.CAMERA_ALT,
                    on_click=lambda _: self.img_picker.pick_files(
                        allowed_extensions=["jpg", "jpeg", "png", "webp"]
                    ),
                ),
                ft.IconButton(
                    icon=ft.icons.CLOSE,
                    tooltip="Remove image",
                    on_click=self._clear_image,
                ),
                ft.ElevatedButton(
                    "Solve with AI",
                    icon=ft.icons.AUTO_AWESOME,
                    on_click=self._ai_solve,
                    bgcolor=ft.colors.PURPLE_700,
                ),
                self.solving_indicator,
            ]),
            ft.Container(
                ft.Column([self.ai_result], scroll=ft.ScrollMode.AUTO),
                bgcolor=ft.colors.WHITE10, border_radius=8,
                padding=12, height=200,
            ),
        ], spacing=6)

    # ── button logic ──────────────────────────────────────────────────────────
    _MAP = {
        "÷": "/", "×": "*", "x²": "**2", "xʸ": "**",
        "π": str(math.pi), "e": str(math.e),
        "√":   "math.sqrt(",
        "sin": "math.sin(math.radians(",
        "cos": "math.cos(math.radians(",
        "tan": "math.tan(math.radians(",
        "log": "math.log10(",
        "ln":  "math.log(",
        "!":   "math.factorial(int(",
        "1/x": "1/(",
    }

    def _btn(self, b):
        if b == "=":
            try:
                result = eval(
                    self.expr,
                    {"__builtins__": {}},
                    {"math": math},
                )
                self.expr = str(result)
                self.display.value = str(round(float(result), 10)).rstrip("0").rstrip(".")
            except Exception:
                self.display.value = "Error"
                self.expr = ""
        elif b in ("C", "CE"):
            self.expr = ""
            self.display.value = "0"
        elif b == "⌫":
            self.expr = self.expr[:-1]
            self.display.value = self.expr or "0"
        elif b == "±":
            self.expr = ("-" + self.expr) if not self.expr.startswith("-") else self.expr[1:]
            self.display.value = self.expr or "0"
        elif b == "%":
            try:
                self.expr = str(eval(self.expr, {"__builtins__": {}}, {}) / 100)
                self.display.value = self.expr
            except Exception:
                pass
        else:
            self.expr += self._MAP.get(b, b)
            self.display.value = self.expr
        self.page.update()

    # ── image helpers ─────────────────────────────────────────────────────────
    def on_image_picked(self, e):
        if not e.files:
            return
        data = read_file(e.files[0])
        if data:
            ext = e.files[0].name.rsplit(".", 1)[-1].lower()
            self.image_mime = "image/png" if ext == "png" else "image/jpeg"
            self.image_b64 = base64.b64encode(data).decode()
            self.img_preview.src_base64 = self.image_b64
            self.img_preview.visible = True
            self.page.update()

    def _clear_image(self, e):
        self.image_b64 = None
        self.img_preview.visible = False
        self.page.update()

    # ── AI solve ──────────────────────────────────────────────────────────────
    def _ai_solve(self, e):
        question = self.ai_input.value.strip()
        if not question and not self.image_b64:
            return

        self.ai_result.value = ""
        self.solving_indicator.visible = True
        self.page.update()

        try:
            client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
            content = []

            if self.image_b64:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": self.image_mime,
                        "data": self.image_b64,
                    },
                })

            content.append({
                "type": "text",
                "text": question if question else
                        "Solve the math problem in this image. Show full step-by-step working.",
            })

            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=(
                    "You are an expert math tutor. Solve problems step by step. "
                    "Cover calculus (derivatives, integrals, limits), algebra, "
                    "geometry, trigonometry, statistics, and linear algebra. "
                    "Format answers clearly with each step numbered."
                ),
                messages=[{"role": "user", "content": content}],
            )
            self.ai_result.value = msg.content[0].text
        except Exception as ex:
            self.ai_result.value = f"Error: {ex}"
        finally:
            self.solving_indicator.visible = False
            self.page.update()


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main(page: ft.Page):
    page.title = "Daily Tools Suite"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 10

    audio_tab = AudioTab(page)
    photo_tab = PhotoTab(page)
    pdf_tab   = PdfTab(page)
    calc_tab  = CalcTab(page)

    # File pickers
    def on_audio_result(e):
        if e.files:
            for f in e.files:
                data = read_file(f)
                if data:
                    audio_tab.tracks.append(AudioSegment.from_file(io.BytesIO(data)))
                    audio_tab.file_list.controls.append(ft.Text(f.name))
            audio_tab.status.value = f"{len(audio_tab.tracks)} track(s) loaded"
            page.update()

    def on_photo_result(e):
        if e.files:
            data = read_file(e.files[0])
            if data:
                photo_tab.curr_img = Image.open(io.BytesIO(data))
                photo_tab._refresh()

    def on_pdf_result(e):
        if e.files:
            for f in e.files:
                if f.path:
                    pdf_tab.paths.append(f.path)
                    pdf_tab.file_list.controls.append(ft.Text(f.name))
            page.update()

    audio_tab.picker = ft.FilePicker(on_result=on_audio_result)
    photo_tab.picker = ft.FilePicker(on_result=on_photo_result)
    pdf_tab.picker   = ft.FilePicker(on_result=on_pdf_result)
    calc_tab.img_picker = ft.FilePicker(on_result=calc_tab.on_image_picked)

    page.overlay.extend([
        audio_tab.picker, photo_tab.picker,
        pdf_tab.picker,   calc_tab.img_picker,
    ])

    page.add(ft.Tabs(
        selected_index=0,
        animation_duration=250,
        expand=True,
        tabs=[
            ft.Tab(text="Calculator", icon=ft.icons.CALCULATE,
                   content=ft.Container(calc_tab.build(), padding=10)),
            ft.Tab(text="Photo",      icon=ft.icons.PHOTO,
                   content=ft.Container(photo_tab.build(), padding=10)),
            ft.Tab(text="Audio",      icon=ft.icons.AUDIOTRACK,
                   content=ft.Container(audio_tab.build(), padding=10)),
            ft.Tab(text="PDF",        icon=ft.icons.PICTURE_AS_PDF,
                   content=ft.Container(pdf_tab.build(), padding=10)),
        ],
    ))


ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8080)
