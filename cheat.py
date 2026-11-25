import ctypes
import ctypes.wintypes
import json
import os
import socket
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox

HOST = "127.0.0.1"
PORT = 2121
CONFIG_FILE = "aether_x_config.json"

# === ОПРЕДЕЛЕНИЕ И СОХРАНЕНИЕ ВЕРСИИ ИГРЫ ===
def get_steam_launch_url():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                appid = json.load(f).get("appid", "4465480")
                return f"steam://rungameid/{appid}//-windowed -noborder -netconport 2121"
        except Exception:
            pass

    r = tk.Tk()
    r.withdraw()
    is_legacy = messagebox.askyesno(
        "AETHER X // Первый запуск",
        "У вас установлена CS:GO как отдельная страница в Steam (Legacy)?\n\n"
        "• ДА — отдельная страница CS:GO Legacy (AppID 4465480)\n"
        "• НЕТ — стандартный CS:GO / CS2 (AppID 730)"
    )
    r.destroy()

    appid = "4465480" if is_legacy else "730"
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"appid": appid}, f)
    return f"steam://rungameid/{appid}//-windowed -noborder -netconport 2121"

STEAM_LAUNCH_URL = get_steam_launch_url()

# === ПОСТОЯННОЕ TCP-СОЕДИНЕНИЕ С CS:GO ===
netcon_sock = None
sock_lock = threading.Lock()

def connect_netcon():
    global netcon_sock
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.35)
        s.connect((HOST, PORT))
        s.setblocking(False)
        netcon_sock = s
        return True
    except Exception:
        netcon_sock = None
        return False

def send_cmd(cmd, silent=False):
    global netcon_sock
    with sock_lock:
        if netcon_sock is None:
            connect_netcon()
        if netcon_sock is not None:
            try:
                try:
                    netcon_sock.recv(4096)
                except Exception:
                    pass
                full = f"sv_cheats 1; {cmd}\n" if not silent else f"{cmd}\n"
                netcon_sock.sendall(full.encode("utf-8"))
                if not silent:
                    status_var.set(f"✔ EXECUTED // {cmd[:48]}")
                    status_lbl.config(fg="#10b981")
                return True
            except Exception:
                try:
                    netcon_sock.close()
                except Exception:
                    pass
                netcon_sock = None
    if not silent:
        status_var.set("✖ OFFLINE // Загрузись на карту в CS:GO")
        status_lbl.config(fg="#ef4444")
    return False

def launch_csgo():
    if netcon_sock is not None or connect_netcon():
        status_var.set("✔ CS:GO уже запущена и подключена!")
        status_lbl.config(fg="#10b981")
        return
    status_var.set("🚀 Запуск CS:GO через Steam с параметрами...")
    status_lbl.config(fg="#facc15")
    try:
        os.startfile(STEAM_LAUNCH_URL)
    except Exception:
        webbrowser.open(STEAM_LAUNCH_URL)

# === ПРЕМИУМ ЦВЕТОВАЯ ПАЛИТРА ===
BG_MAIN = "#090b10"
BG_SIDEBAR = "#0e1118"
BG_CARD = "#141824"
ACCENT = "#8b5cf6"
ACCENT_GLOW = "#a78bfa"
CYAN = "#06b6d4"
TEXT_MAIN = "#f8fafc"
TEXT_DIM = "#64748b"
GREEN = "#10b981"
RED = "#ef4444"

# Открывается сразу в левом верхнем углу (+25+25), чтобы не мешать центру экрана
DEFAULT_GEOM = "680x490+25+25"
root = tk.Tk()
root.title("AETHER X // ULTIMATE SUITE")
root.geometry(DEFAULT_GEOM)
root.configure(bg=BG_MAIN)
root.overrideredirect(True)
root.attributes("-topmost", True)
root.attributes("-alpha", 0.97)

# === ЗАЩИТА ОТ ВЫЛЕТОВ ===
def safe_excepthook(exc_type, exc_val, exc_tb):
    try:
        status_var.set(f"⚠ RECOVERED: {exc_val}")
    except Exception:
        pass

sys.excepthook = safe_excepthook

# === ПЕРЕТАСКИВАНИЕ ОКНА ЗА ЛЮБОЕ ПУСТОЕ МЕСТО ===
def start_move(e):
    if isinstance(e.widget, (tk.Tk, tk.Frame, tk.Label)):
        root.x = e.x_root - root.winfo_x()
        root.y = e.y_root - root.winfo_y()

def do_move(e):
    if hasattr(root, "x") and isinstance(e.widget, (tk.Tk, tk.Frame, tk.Label)):
        root.geometry(f"+{e.x_root - root.x}+{e.y_root - root.y}")

root.bind("<ButtonPress-1>", start_move)
root.bind("<B1-Motion>", do_move)

# === НЕУБИВАЕМЫЙ TOGGLE НА INSERT + АВТО-КУРСОР ===
visible = True
saved_geom = DEFAULT_GEOM

def toggle_overlay():
    global visible, saved_geom
    if visible:
        saved_geom = root.geometry()
        root.attributes("-alpha", 0.0)
        root.geometry("1x1+-100+-100")
        send_cmd("gameui_hide", silent=True)
        visible = False
    else:
        send_cmd("gameui_activate", silent=True)
        root.geometry(saved_geom)
        root.attributes("-alpha", 0.97)
        root.lift()
        root.attributes("-topmost", True)
        root.focus_force()
        visible = True

def hotkey_loop():
    u32 = ctypes.windll.user32
    if not u32.RegisterHotKey(None, 1, 0x4000, 0x2D):
        u32.RegisterHotKey(None, 1, 0, 0x2D)
    msg = ctypes.wintypes.MSG()
    while u32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        if msg.message == 0x0312 and msg.wParam == 1:
            root.after(0, toggle_overlay)
        u32.TranslateMessage(ctypes.byref(msg))
        u32.DispatchMessageW(ctypes.byref(msg))

threading.Thread(target=hotkey_loop, daemon=True).start()
# === ПРОВЕРКА СВЯЗИ С ИГРОЙ ===
def check_connection():
    with sock_lock:
        connected = netcon_sock is not None or connect_netcon()
    if connected:
        conn_lbl.config(text="● CS:GO ONLINE", fg=GREEN)
    else:
        conn_lbl.config(text="● CS:GO OFFLINE", fg=RED)
    root.after(1500, check_connection)

# === ВЕРХНЯЯ ШАПКА ===
topbar = tk.Frame(root, bg="#050609", height=38)
topbar.pack(fill="x")

title_lbl = tk.Label(topbar, text="  ✦ AETHER X  //  [INSERT] МЕНЮ + КУРСОР",
                     bg="#050609", fg=ACCENT_GLOW, font=("Consolas", 10, "bold"))
title_lbl.pack(side="left", pady=8)

close_btn = tk.Button(topbar, text="✕", bg="#050609", fg=TEXT_DIM, activebackground=RED,
                      activeforeground="white", bd=0, font=("Arial", 11, "bold"), width=4,
                      command=root.destroy)
close_btn.pack(side="right", fill="y")

# Кнопка мгновенного сброса в левый верхний угол экрана
tk.Button(topbar, text="◰ В УГОЛ", bg="#1e2534", fg=ACCENT_GLOW, bd=0,
          font=("Consolas", 8, "bold"), padx=8, cursor="hand2",
          command=lambda: root.geometry(DEFAULT_GEOM)).pack(side="right", padx=4, pady=6)

conn_lbl = tk.Label(topbar, text="● CHECKING...", bg="#050609", fg=TEXT_DIM, font=("Consolas", 8, "bold"))
conn_lbl.pack(side="right", padx=10)

# === ОСНОВНОЙ КАРКАС ===
body = tk.Frame(root, bg=BG_MAIN)
body.pack(fill="both", expand=True)

sidebar = tk.Frame(body, bg=BG_SIDEBAR, width=180)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)

content = tk.Frame(body, bg=BG_MAIN)
content.pack(side="right", fill="both", expand=True, padx=14, pady=10)

footer = tk.Frame(root, bg="#050609", height=25)
footer.pack(fill="x", side="bottom")
status_var = tk.StringVar(value="AETHER X READY // Загрузись на карту и жми кнопки")
status_lbl = tk.Label(footer, textvariable=status_var, bg="#050609", fg=TEXT_DIM, font=("Consolas", 8))
status_lbl.pack(side="left", padx=10, pady=3)

# === КАСТОМНЫЕ ЭЛЕМЕНТЫ UI ===
toggle_states = {}

def add_toggle(parent, key, title, subtitle, cmd_on, cmd_off):
    toggle_states[key] = False
    card = tk.Frame(parent, bg=BG_CARD, pady=5, padx=10)
    card.pack(fill="x", pady=2)

    text_box = tk.Frame(card, bg=BG_CARD)
    text_box.pack(side="left", fill="x", expand=True)
    tk.Label(text_box, text=title, bg=BG_CARD, fg=TEXT_MAIN, font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x")
    tk.Label(text_box, text=subtitle, bg=BG_CARD, fg=TEXT_DIM, font=("Segoe UI", 8), anchor="w").pack(fill="x")

    switch = tk.Canvas(card, width=44, height=22, bg=BG_CARD, highlightthickness=0, cursor="hand2")
    switch.pack(side="right", padx=4)

    def draw_switch(state):
        switch.delete("all")
        bg_c = ACCENT if state else "#283044"
        knob_x = 24 if state else 4
        switch.create_oval(2, 2, 20, 20, fill=bg_c, outline="")
        switch.create_oval(24, 2, 42, 20, fill=bg_c, outline="")
        switch.create_rectangle(11, 2, 33, 20, fill=bg_c, outline="")
        switch.create_oval(knob_x, 4, knob_x + 16, 18, fill="white", outline="")

    draw_switch(False)

    def on_click(event=None):
        toggle_states[key] = not toggle_states[key]
        st = toggle_states[key]
        draw_switch(st)
        send_cmd(cmd_on if st else cmd_off)

    switch.bind("<Button-1>", on_click)

def add_slider(parent, title, from_val, to_val, default_val, cmd_template):
    card = tk.Frame(parent, bg=BG_CARD, pady=5, padx=10)
    card.pack(fill="x", pady=2)

    top = tk.Frame(card, bg=BG_CARD)
    top.pack(fill="x")
    tk.Label(top, text=title, bg=BG_CARD, fg=TEXT_MAIN, font=("Segoe UI", 9, "bold")).pack(side="left")
    val_lbl = tk.Label(top, text=str(default_val), bg=BG_CARD, fg=ACCENT_GLOW, font=("Consolas", 9, "bold"))
    val_lbl.pack(side="right")

    def on_slide(val):
        v = int(float(val))
        val_lbl.config(text=str(v))
        send_cmd(cmd_template.format(v))

    scale = tk.Scale(card, from_=from_val, to=to_val, orient="horizontal", showvalue=False,
                     bg=BG_CARD, fg=ACCENT, troughcolor="#283044", activebackground=ACCENT_GLOW,
                     highlightthickness=0, bd=0, command=on_slide)
    scale.set(default_val)
    scale.pack(fill="x", pady=(2, 0))

def add_action_btn(parent, text, cmd, color="#232a3b"):
    btn = tk.Button(parent, text=text, bg=color, fg="white", activebackground=ACCENT,
                    activeforeground="white", bd=0, font=("Segoe UI", 9, "bold"), pady=6,
                    cursor="hand2", command=lambda: send_cmd(cmd))
    btn.pack(fill="x", pady=2)

# === ВКЛАДКИ ===
tabs = {}
tab_buttons = {}

def switch_tab(name):
    for t in tabs.values():
        t.pack_forget()
    for k, b in tab_buttons.items():
        b.config(bg=BG_SIDEBAR, fg=TEXT_DIM)
    tabs[name].pack(fill="both", expand=True)
    tab_buttons[name].config(bg=BG_CARD, fg=TEXT_MAIN)

def create_tab(name, label):
    frame = tk.Frame(content, bg=BG_MAIN)
    tabs[name] = frame
    btn = tk.Button(sidebar, text=f"  {label}", anchor="w", bg=BG_SIDEBAR, fg=TEXT_DIM,
                    activebackground=BG_CARD, activeforeground=TEXT_MAIN, bd=0,
                    font=("Segoe UI", 9, "bold"), pady=8, padx=10, cursor="hand2",
                    command=lambda: switch_tab(name))
    btn.pack(fill="x", pady=1)
    tab_buttons[name] = btn
    return frame

# Быстрые кнопки в сайдбаре
tk.Button(sidebar, text="▶ ЗАПУСТИТЬ CS:GO", bg="#2563eb", fg="white",
          activebackground="#1d4ed8", bd=0, font=("Segoe UI", 8, "bold"), pady=7,
          cursor="hand2", command=launch_csgo).pack(fill="x", padx=8, pady=(8, 3))

tk.Button(sidebar, text="🔪 НОЖ + АВТО-БХОП", bg=CYAN, fg="#042f2e",
          activebackground="#0891b2", bd=0, font=("Segoe UI", 8, "bold"), pady=7,
          cursor="hand2", command=lambda: send_cmd("mp_drop_knife_enable 1; give weapon_knife_karambit; ent_fire weapon_knife addoutput \"classname weapon_knifegg\"; sv_autobunnyhopping 1; sv_enablebunnyhopping 1")
          ).pack(fill="x", padx=8, pady=(3, 8))
# 1. VISUALS & RADAR
t_vis = create_tab("vis", "👁  VISUALS & RADAR")
add_toggle(t_vis, "wh", "Wallhack (X-Ray Models)", "Подсветка моделей игроков сквозь стены",
           "r_drawothermodels 2", "r_drawothermodels 1")
add_toggle(t_vis, "radar", "Radar Hack (Все враги на карте)", "Отображает всех противников на радаре",
           "mp_radar_showall 1", "mp_radar_showall 0")
add_toggle(t_vis, "skel", "Skeleton ESP", "Показывает скелеты и кости игроков",
           "enable_skeleton_draw 1", "enable_skeleton_draw 0")
add_toggle(t_vis, "imp", "Прострелы и траектория гранат", "Показывает точки попадания пуль сквозь стены",
           "sv_showimpacts 1; sv_grenade_trajectory 1", "sv_showimpacts 0; sv_grenade_trajectory 0")
add_toggle(t_vis, "fls", "Анти-Флеш и Анти-Дым", "Убирает ослепление и туман",
           "mat_fillrate 1; fog_enable 0", "mat_fillrate 0; fog_enable 1")
add_toggle(t_vis, "tp", "Вид от 3-го лица (Thirdperson)", "Камера со спины (видно за углами)",
           "thirdperson", "firstperson")

# 2. GOD & COMBAT
t_god = create_tab("god", "🛡  GOD & COMBAT")
add_action_btn(t_god, "🛡  БЕССМЕРТИЕ (God Mode ВКЛ / ВЫКЛ)", "god", color=ACCENT)
add_action_btn(t_god, "❤️  НЕУЯЗВИМОСТЬ (HP не падает ниже 1)", "buddha")
add_action_btn(t_god, "💉  100 HP + ПОЛНАЯ БРОНЯ", "give item_assaultsuit; hurtme -100")
add_toggle(t_god, "one", "One-Shot Kill (Убийство с 1 пули)", "Любое попадание убивает мгновенно",
           "mp_damage_scale_ct_body 100; mp_damage_scale_ct_head 100; mp_damage_scale_t_body 100; mp_damage_scale_t_head 100",
           "mp_damage_scale_ct_body 1; mp_damage_scale_ct_head 1; mp_damage_scale_t_body 1; mp_damage_scale_t_head 1")
add_toggle(t_god, "rec", "No Recoil & No Spread (0 Отдачи)", "Пули летят точно в центр прицела",
           "weapon_accuracy_nospread 1; weapon_recoil_scale 0; weapon_recoil_view_punch_extra 0",
           "weapon_accuracy_nospread 0; weapon_recoil_scale 2; weapon_recoil_view_punch_extra 0.055")
add_toggle(t_god, "amm", "Бесконечные патроны (Без перезарядки)", "Патроны не заканчиваются",
           "sv_infinite_ammo 1", "sv_infinite_ammo 0")

# 3. ARSENAL & KNIVES (ВСЕ ПУЛЕМЁТЫ И НОЖИ)
t_gun = create_tab("gun", "🔫  ARSENAL & KNIVES")

def add_gun_group(title, guns, is_knife=False):
    tk.Label(t_gun, text=title, bg=BG_MAIN, fg=ACCENT_GLOW, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(3, 1))
    row = tk.Frame(t_gun, bg=BG_MAIN)
    row.pack(fill="x", pady=2)
    for g_name, g_id in guns:
        if is_knife:
            cmd = f"mp_drop_knife_enable 1; give {g_id}; ent_fire weapon_knife addoutput \"classname weapon_knifegg\""
        else:
            cmd = f"sv_infinite_ammo 1; weapon_accuracy_nospread 1; weapon_recoil_scale 0; weapon_recoil_view_punch_extra 0; give {g_id}"
        tk.Button(row, text=g_name, bg="#1e2534", fg="white", activebackground=ACCENT,
                  bd=0, font=("Segoe UI", 8, "bold"), pady=5, cursor="hand2",
                  command=lambda c=cmd: send_cmd(c)).pack(side="left", expand=True, fill="x", padx=2)

add_gun_group("ВСЕ ПУЛЕМЁТЫ (0 отдачи + беск. патроны):", [
    ("NEGEV", "weapon_negev"), ("M249", "weapon_m249")
])
add_gun_group("ШТУРМОВЫЕ ВИНТОВКИ:", [
    ("AK-47", "weapon_ak47"), ("M4A4", "weapon_m4a1"), ("M4A1-S", "weapon_m4a1_silencer"), ("AUG", "weapon_aug"), ("SG 553", "weapon_sg556")
])
add_gun_group("СНАЙПЕРКИ И ПИСТОЛЕТЫ:", [
    ("AWP", "weapon_awp"), ("SCAR-20", "weapon_scar20"), ("G3SG1", "weapon_g3sg1"), ("Deagle", "weapon_deagle"), ("R8", "weapon_revolver")
])
add_gun_group("КАСТОМНЫЕ НОЖИ (Выкинь старый нож на G):", [
    ("Керамбит", "weapon_knife_karambit"), ("Бабочка", "weapon_knife_butterfly"),
    ("M9 Штык", "weapon_knife_m9_bayonet"), ("Скелетный", "weapon_knife_skeleton")
], is_knife=True)

# 4. MOVEMENT
t_mov = create_tab("mov", "🚀  MOVEMENT")
add_toggle(t_mov, "bhp", "Авто-Баннихоп (BunnyHop)", "Зажми пробел для идеальных прыжков",
           "sv_autobunnyhopping 1; sv_enablebunnyhopping 1", "sv_autobunnyhopping 0; sv_enablebunnyhopping 0")
add_action_btn(t_mov, "✈  ПОЛЁТ СКВОЗЬ СТЕНЫ (Noclip)", "noclip", color=ACCENT)
add_slider(t_mov, "Скорость бега (320 = стандарт)", 320, 1500, 320,
           "sv_maxspeed {0}; cl_forwardspeed {0}; cl_backspeed {0}; cl_sidespeed {0}")
add_slider(t_mov, "Гравитация (800 = норма, 200 = луна)", 100, 800, 800, "sv_gravity {0}")

# 5. BOTS MANAGER
t_bot = create_tab("bot", "🤖  BOTS MANAGER")
spawn_card = tk.Frame(t_bot, bg=BG_CARD, pady=7, padx=10)
spawn_card.pack(fill="x", pady=2)
tk.Label(spawn_card, text="КАСТОМНЫЙ СПАВН БОТОВ (Количество + Сложность + Команда)",
         bg=BG_CARD, fg=ACCENT_GLOW, font=("Segoe UI", 8, "bold")).pack(anchor="w")

ctrl_row = tk.Frame(spawn_card, bg=BG_CARD)
ctrl_row.pack(fill="x", pady=(5, 4))
tk.Label(ctrl_row, text="Кол-во:", bg=BG_CARD, fg=TEXT_MAIN, font=("Segoe UI", 8)).pack(side="left")
bot_count_var = tk.StringVar(value="5")
tk.Entry(ctrl_row, textvariable=bot_count_var, width=4, bg="#232a3b", fg="white",
         insertbackground="white", bd=0, justify="center", font=("Consolas", 9, "bold")).pack(side="left", padx=6)

tk.Label(ctrl_row, text="Сложность:", bg=BG_CARD, fg=TEXT_MAIN, font=("Segoe UI", 8)).pack(side="left", padx=(6, 2))
diff_var = tk.StringVar(value="3 (Expert)")
diff_map = {"0 (Easy)": 0, "1 (Normal)": 1, "2 (Hard)": 2, "3 (Expert)": 3}
diff_menu = tk.OptionMenu(ctrl_row, diff_var, *diff_map.keys())
diff_menu.config(bg="#232a3b", fg="white", bd=0, highlightthickness=0, font=("Segoe UI", 8))
diff_menu["menu"].config(bg="#232a3b", fg="white")
diff_menu.pack(side="left", padx=4)

def spawn_custom_bots(team):
    try:
        cnt = max(1, min(30, int(bot_count_var.get())))
    except ValueError:
        cnt = 1
    d_val = diff_map.get(diff_var.get(), 3)
    cmds = [f"mp_autoteambalance 0; mp_limitteams 0; bot_difficulty {d_val}"]
    for _ in range(cnt):
        cmds.append(f"bot_add_{team}")
    send_cmd("; ".join(cmds))

team_btn_row = tk.Frame(spawn_card, bg=BG_CARD)
team_btn_row.pack(fill="x", pady=(2, 0))
tk.Button(team_btn_row, text="🟠 СПАВН ЗА T", bg="#d97706", fg="white", bd=0,
          font=("Segoe UI", 8, "bold"), pady=5, cursor="hand2",
          command=lambda: spawn_custom_bots("t")).pack(side="left", expand=True, fill="x", padx=(0, 3))
tk.Button(team_btn_row, text="🔵 СПАВН ЗА CT", bg="#2563eb", fg="white", bd=0,
          font=("Segoe UI", 8, "bold"), pady=5, cursor="hand2",
          command=lambda: spawn_custom_bots("ct")).pack(side="left", expand=True, fill="x", padx=(3, 0))

add_toggle(t_bot, "b_frz", "Заморозить всех ботов", "Боты стоят на месте", "bot_stop 1", "bot_stop 0")
add_toggle(t_bot, "b_knf", "Зомби-боты (Только с ножами)", "Боты атакуют только ножами", "bot_knives_only", "bot_all_weapons")
add_action_btn(t_bot, "🎯  ТЕЛЕПОРТ БОТА В ПРИЦЕЛ", "bot_place", color=ACCENT)

bot_row = tk.Frame(t_bot, bg=BG_MAIN)
bot_row.pack(fill="x", pady=2)
tk.Button(bot_row, text="💀 УБИТЬ БОТОВ", bg="#232a3b", fg="white", activebackground=RED, bd=0,
          font=("Segoe UI", 8, "bold"), pady=6, cursor="hand2", command=lambda: send_cmd("bot_kill")
          ).pack(side="left", expand=True, fill="x", padx=(0, 2))
tk.Button(bot_row, text="🚫 КИКНУТЬ БОТОВ", bg="#232a3b", fg="white", activebackground=RED, bd=0,
          font=("Segoe UI", 8, "bold"), pady=6, cursor="hand2", command=lambda: send_cmd("bot_kick")
          ).pack(side="left", expand=True, fill="x", padx=(2, 0))

# 6. RAGE & PARTY
t_rag = create_tab("rag", "🔥  RAGE & PARTY")
add_toggle(t_rag, "spin", "ТУРБО-КРУТИЛКА (15000 Speed)", "Безумная скорость вращения камеры",
           "cl_yawspeed 15000; +right", "-right; cl_yawspeed 210")
add_toggle(t_rag, "slowmo", "Замедление времени (0.3x)", "Эффект матрицы для всех",
           "host_timescale 0.3", "host_timescale 1.0")
add_action_btn(t_rag, "💰  65535$ + ПОКУПКА ВЕЗДЕ + РАУНД 60 МИН",
               "mp_maxmoney 65535; mp_startmoney 65535; mp_roundtime_defuse 60; mp_buy_anywhere 1; mp_restartgame 1", color=ACCENT)
add_action_btn(t_rag, "💣  ВСЕ ГРАНАТЫ + ПОЛНАЯ БРОНЯ",
               "give item_assaultsuit; give weapon_hegrenade; give weapon_flashbang; give weapon_smokegrenade; give weapon_molotov")

# Запуск
switch_tab("vis")
check_connection()
root.after(700, launch_csgo)

root.mainloop()
