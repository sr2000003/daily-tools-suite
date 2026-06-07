import flet as ft
from pydub import AudioSegment
from PIL import Image, ImageOps, ImageEnhance
from PyPDF2 import PdfMerger
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
        super().__init__(expand=True, scroll="auto")
        self._pg = page
        self.tracks = []
        self.status = ft.Text("Audio Studio: Ready", color=ft.Colors.BLUE_200)
        self.file_list = ft.ListView(expand=True, spacing=5)
        self.fade_in = ft.TextField(label="Fade In (ms)", value="1000", width=130)
        self.fade_out = ft.TextField(label="Fade Out (ms)", value="1000", width=130)

    def build(self):
        return ft.Column([
            ft.Text("Audio Editor", size=25, weight="bold"),
            ft.Row([
                ft.ElevatedButton("Add Track", icon=ft.Icons.ADD,
                                  on_click=lambda _: self.picker.pick_files(allow_multiple=True)),
                self.status,
            ]),
            ft.Container(self.file_list, bgcolor=ft.Colors.WHITE10,
                         border_radius=10, padding=10, height=150),
            ft.Text("Effects"),
            ft.Row([self.fade_in, self.fade_out]),
            ft.ElevatedButton("Join & Export", icon=ft.Icons.SAVE,
                              on_click=self.export_audio, bgcolor=ft.Colors.BLUE_800),
        ])

    def export_audio(self, e):
        if not self.tracks:
            return
        combined = self.tracks[0]
        for t in self.tracks[1:]:
            combined = combined.append(t, crossfade=100)
        try:
            fade_in_ms = int(self.fade_in.value)
        except (TypeError, ValueError):
            fade_in_ms = 0
        try:
            fade_out_ms = int(self.fade_out.value)
        except (TypeError, ValueError):
            fade_out_ms = 0
        if fade_in_ms > 0:
            combined = combined.fade_in(fade_in_ms)
        if fade_out_ms > 0:
            combined = combined.fade_out(fade_out_ms)
        path = "Combined_Audio.mp3"
        combined.export(path, format="mp3")
        self._pg.snack_bar = ft.SnackBar(ft.Text(f"Exported: {path}"))
        self._pg.snack_bar.open = True
        self._pg.update()


# ── PHOTO TAB ─────────────────────────────────────────────────────────────────
class PhotoTab(ft.Column):
    def __init__(self, page):
        super().__init__(expand=True, scroll="auto")
        self._pg = page
        self.curr_img = None
        self.img_display = ft.Image(src="", width=300, height=300, fit="contain")

    def build(self):
        return ft.Column([
            ft.Text("Lumina Photo Editor", size=25, weight="bold"),
            ft.Container(self.img_display, bgcolor=ft.Colors.BLACK38, border_radius=10),
            ft.Row([
                ft.IconButton(ft.Icons.BRIGHTNESS_6, tooltip="Brighten",
                              on_click=lambda _: self.apply("bright")),
                ft.IconButton(ft.Icons.COLOR_LENS, tooltip="Sepia",
                              on_click=lambda _: self.apply("sepia")),
                ft.IconButton(ft.Icons.CONTRAST, tooltip="Contrast",
                              on_click=lambda _: self.apply("contrast")),
                ft.IconButton(ft.Icons.ROTATE_RIGHT, tooltip="Rotate",
                              on_click=lambda _: self.apply("rotate")),
            ], alignment="center"),
            ft.Row([
                ft.ElevatedButton("Open Photo", icon=ft.Icons.IMAGE,
                                  on_click=lambda _: self.picker.pick_files(
                                      allowed_extensions=["jpg", "jpeg", "png", "bmp", "gif"])),
                ft.ElevatedButton("Save", icon=ft.Icons.SAVE,
                                  on_click=self.save, bgcolor=ft.Colors.GREEN_700),
            ], alignment="center"),
        ], horizontal_alignment="center")

    def save(self, e):
        if not self.curr_img:
            return
        path = "Edited_Photo.png"
        self.curr_img.convert("RGB").save(path, format="PNG")
        self._pg.snack_bar = ft.SnackBar(ft.Text(f"Saved: {path}"))
        self._pg.snack_bar.open = True
        self._pg.update()

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
        self._pg.update()


# ── PDF TAB ───────────────────────────────────────────────────────────────────
class PdfTab(ft.Column):
    def __init__(self, page):
        super().__init__(expand=True, scroll="auto")
        self._pg = page
        self.paths = []
        self.file_list = ft.ListView(spacing=4, height=120)

    def build(self):
        return ft.Column([
            ft.Text("PDF Merger", size=25, weight="bold"),
            ft.ElevatedButton("Select PDFs", icon=ft.Icons.FILE_COPY,
                              on_click=lambda _: self.picker.pick_files(
                                  allow_multiple=True, allowed_extensions=["pdf"])),
            ft.Container(self.file_list, bgcolor=ft.Colors.WHITE10,
                         border_radius=8, padding=8, height=130),
            ft.ElevatedButton("Merge & Save", icon=ft.Icons.MERGE_TYPE,
                              on_click=self.merge, bgcolor=ft.Colors.GREEN_700),
        ])

    def merge(self, e):
        if not self.paths:
            return
        m = PdfMerger()
        for p in self.paths:
            m.append(p)
        out = "Merged.pdf"
        m.write(out)
        self._pg.snack_bar = ft.SnackBar(ft.Text(f"Saved: {out}"))
        self._pg.snack_bar.open = True
        self._pg.update()


# ── CALCULATOR TAB ────────────────────────────────────────────────────────────
class CalcTab(ft.Column):
    def __init__(self, page):
        super().__init__(expand=True, scroll="auto")
        self._pg = page
        self.expr = ""
        self.history = ft.ListView(spacing=4, height=120)

        self.display = ft.TextField(
            value="0", read_only=True, text_size=28,
            text_align="right",
            bgcolor=ft.Colors.BLACK54, border_radius=8,
        )

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
                    b,
                    expand=True,
                    height=48,
                    on_click=lambda e, b=b: self._btn(b),
                    style=ft.ButtonStyle(
                        bgcolor=(
                            ft.Colors.GREEN_700 if b == "=" else
                            ft.Colors.ORANGE_700 if b in ["÷", "×", "-", "+"] else
                            ft.Colors.RED_700 if b in ["C", "CE", "⌫"] else
                            ft.Colors.BLUE_GREY_700
                        )
                    ),
                ) for b in row
            ], spacing=3))

        return ft.Column([
            ft.Text("Scientific Calculator", size=22, weight="bold"),
            self.display,
            ft.Column(rows, spacing=3),
            ft.Divider(height=12),
            ft.Text("History", size=14, color=ft.Colors.GREY_400),
            ft.Container(self.history, bgcolor=ft.Colors.WHITE10,
                         border_radius=8, padding=8),
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
                prev = self.expr
                result = eval(
                    self.expr,
                    {"__builtins__": {}},
                    {"math": math},
                )
                ans = str(round(float(result), 10)).rstrip("0").rstrip(".")
                self.history.controls.insert(0, ft.Text(f"{prev} = {ans}", size=12, color=ft.Colors.GREY_300))
                self.expr = ans
                self.display.value = ans
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
        self._pg.update()



# ── MAIN ──────────────────────────────────────────────────────────────────────
def main(page: ft.Page):
    page.title = "Daily Tools Suite"
    page.theme_mode = "dark"
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

    audio_tab.picker = ft.FilePicker()
    audio_tab.picker.on_result = on_audio_result
    photo_tab.picker = ft.FilePicker()
    photo_tab.picker.on_result = on_photo_result
    pdf_tab.picker = ft.FilePicker()
    pdf_tab.picker.on_result = on_pdf_result

    page.overlay.extend([
        audio_tab.picker, photo_tab.picker, pdf_tab.picker,
    ])

    panels = [
        ft.Container(calc_tab.build(),  padding=10, expand=True, visible=True),
        ft.Container(photo_tab.build(), padding=10, expand=True, visible=False),
        ft.Container(audio_tab.build(), padding=10, expand=True, visible=False),
        ft.Container(pdf_tab.build(),   padding=10, expand=True, visible=False),
    ]

    nav_labels = [
        ("Calculator", ft.Icons.CALCULATE),
        ("Photo",      ft.Icons.PHOTO),
        ("Audio",      ft.Icons.AUDIOTRACK),
        ("PDF",        ft.Icons.PICTURE_AS_PDF),
    ]
    nav_buttons = []

    def select_tab(index):
        for i, p in enumerate(panels):
            p.visible = (i == index)
        for i, b in enumerate(nav_buttons):
            b.bgcolor = ft.Colors.BLUE_800 if i == index else ft.Colors.BLUE_GREY_700
        page.update()

    for i, (label, icon) in enumerate(nav_labels):
        nav_buttons.append(ft.ElevatedButton(
            label, icon=icon,
            bgcolor=ft.Colors.BLUE_800 if i == 0 else ft.Colors.BLUE_GREY_700,
            on_click=lambda _, i=i: select_tab(i),
        ))

    page.add(ft.Row(nav_buttons), ft.Column(panels, expand=True))


ft.app(target=main, view="web_browser", host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
