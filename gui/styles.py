"""
Visual design constants and ttk style configurations for ClashBoard.
Enforces the specification:
- Theme: clam
- Accent color: #2F5233 (deep forest green)
- Background: #F7F6F2 (warm off-white)
- Text: #1C1C1C
- Muted subject palette: Dusty Blue, Terracotta, Sage, Mustard, Slate
- Segoe UI typography
"""
import tkinter.ttk as ttk

# Color Palette
BG_COLOR = '#F7F6F2'
SIDEBAR_BG = '#EBE9E2'
SIDEBAR_ACTIVE = '#2F5233'
CARD_BG = '#FFFFFF'
TEXT_COLOR = '#1C1C1C'
MUTED_TEXT = '#5A5A5A'
BORDER_COLOR = '#D5D3CB'
ACCENT_COLOR = '#2F5233'
ACCENT_HOVER = '#3E6B45'

# Status Colors
STATUS_DONE = '#38761D'
STATUS_PLANNED = '#2F5233'
STATUS_MISSED = '#B84A39'
STATUS_CLASH = '#C25438'
STATUS_WARNING = '#D9822B'

# Subject Muted Palette
SUBJECT_PALETTE = [
    ('#5B84B1', '#EBF1F7'),  # Dusty Blue (Border/Accent, Fill)
    ('#D46A43', '#FCEEE8'),  # Terracotta
    ('#7A9A78', '#EEF4EE'),  # Sage
    ('#D9A74A', '#FAF5EB'),  # Mustard
    ('#6B7A82', '#EFF1F3'),  # Slate
    ('#93708D', '#F6EFF5'),  # Mauve
    ('#8B7355', '#F5F1EB'),  # Sandstone
]


def get_subject_colors(subject_id_or_idx):
    """Returns (primary_color, light_tint_fill) for a subject."""
    idx = int(subject_id_or_idx or 0) % len(SUBJECT_PALETTE)
    return SUBJECT_PALETTE[idx]


def apply_theme(root):
    """Configures global ttk style with Clam theme and ClashBoard design rules."""
    style = ttk.Style(root)
    try:
        style.theme_use('clam')
    except Exception:
        pass

    # Root window background
    root.configure(background=BG_COLOR)

    # Frame
    style.configure('TFrame', background=BG_COLOR)
    style.configure('Card.TFrame', background=CARD_BG, relief='flat')
    style.configure('Sidebar.TFrame', background=SIDEBAR_BG)

    # Label
    style.configure('TLabel', background=BG_COLOR, foreground=TEXT_COLOR, font=('Segoe UI', 10))
    style.configure('Card.TLabel', background=CARD_BG, foreground=TEXT_COLOR, font=('Segoe UI', 10))
    style.configure('Header.TLabel', font=('Segoe UI', 14, 'bold'), foreground=ACCENT_COLOR, background=BG_COLOR)
    style.configure('SubHeader.TLabel', font=('Segoe UI', 11, 'bold'), foreground=TEXT_COLOR, background=BG_COLOR)
    style.configure('Title.TLabel', font=('Segoe UI', 18, 'bold'), foreground=ACCENT_COLOR, background=BG_COLOR)
    style.configure('Muted.TLabel', font=('Segoe UI', 9), foreground=MUTED_TEXT, background=BG_COLOR)
    style.configure('CardMuted.TLabel', font=('Segoe UI', 9), foreground=MUTED_TEXT, background=CARD_BG)
    style.configure('Badge.TLabel', font=('Segoe UI', 9, 'bold'), foreground='white', background=STATUS_MISSED, padding=(6, 2))

    # Buttons
    # Accent Primary Button
    style.configure(
        'Accent.TButton',
        background=ACCENT_COLOR,
        foreground='white',
        font=('Segoe UI', 10, 'bold'),
        relief='flat',
        padding=8,
        borderwidth=0
    )
    style.map(
        'Accent.TButton',
        background=[('active', ACCENT_HOVER), ('pressed', '#233E26'), ('disabled', '#A0AFA2')]
    )

    # Secondary Button
    style.configure(
        'Secondary.TButton',
        background='#E8E6DF',
        foreground=TEXT_COLOR,
        font=('Segoe UI', 10),
        relief='flat',
        padding=7,
        borderwidth=1,
        bordercolor=BORDER_COLOR
    )
    style.map(
        'Secondary.TButton',
        background=[('active', '#DDDCD4'), ('pressed', '#CECCC3')]
    )

    # Danger Button
    style.configure(
        'Danger.TButton',
        background='#B84A39',
        foreground='white',
        font=('Segoe UI', 10, 'bold'),
        relief='flat',
        padding=7
    )
    style.map(
        'Danger.TButton',
        background=[('active', '#9C3E30'), ('pressed', '#7D2E23')]
    )

    # Sidebar Nav Buttons
    style.configure(
        'Nav.TButton',
        background=SIDEBAR_BG,
        foreground=TEXT_COLOR,
        font=('Segoe UI', 11),
        relief='flat',
        anchor='w',
        padding=(14, 10),
        borderwidth=0
    )
    style.map(
        'Nav.TButton',
        background=[('active', '#E0DDD4'), ('pressed', '#D5D1C6')]
    )

    style.configure(
        'NavActive.TButton',
        background=ACCENT_COLOR,
        foreground='white',
        font=('Segoe UI', 11, 'bold'),
        relief='flat',
        anchor='w',
        padding=(14, 10),
        borderwidth=0
    )
    style.map(
        'NavActive.TButton',
        background=[('active', ACCENT_HOVER)]
    )

    # LabelFrame
    style.configure(
        'TLabelframe',
        background=BG_COLOR,
        relief='groove',
        borderwidth=1,
        bordercolor=BORDER_COLOR
    )
    style.configure(
        'TLabelframe.Label',
        font=('Segoe UI', 10, 'bold'),
        foreground=ACCENT_COLOR,
        background=BG_COLOR
    )

    # Entry & Combobox
    style.configure('TEntry', font=('Segoe UI', 10), fieldbackground='#FFFFFF', padding=5)
    style.configure('TCombobox', font=('Segoe UI', 10), fieldbackground='#FFFFFF', padding=4)
    style.map('TCombobox', fieldbackground=[('readonly', '#FFFFFF')])

    # Scale
    style.configure('Horizontal.TScale', background=BG_COLOR, troughcolor='#DCDAD2', slidercolor=ACCENT_COLOR)

    # Treeview
    style.configure(
        'Treeview',
        background='#FFFFFF',
        fieldbackground='#FFFFFF',
        foreground=TEXT_COLOR,
        font=('Segoe UI', 9),
        rowheight=28,
        borderwidth=1,
        relief='solid',
        bordercolor=BORDER_COLOR
    )
    style.configure(
        'Treeview.Heading',
        font=('Segoe UI', 10, 'bold'),
        background='#EAE8E0',
        foreground=TEXT_COLOR,
        padding=6,
        relief='flat'
    )
    style.map(
        'Treeview',
        background=[('selected', '#2F5233')],
        foreground=[('selected', '#FFFFFF')]
    )

    return style

