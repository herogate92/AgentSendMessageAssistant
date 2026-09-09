import ctypes
from ctypes import wintypes
import datetime
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
import winsound

# Win32 API 선언
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.GetForegroundWindow.restype = wintypes.HWND
user32.WindowFromPoint.argtypes = [wintypes.POINT]
user32.WindowFromPoint.restype = wintypes.HWND
user32.GetAncestor.argtypes = [wintypes.HWND, ctypes.c_uint]
user32.GetAncestor.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.IsWindow.argtypes = [wintypes.HWND]
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
kernel32.GetCurrentThreadId.restype = wintypes.DWORD

# 64비트 호환 메모리 및 클립보드 API 타입 선언
kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = ctypes.c_void_p

kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalLock.restype = ctypes.c_void_p

kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.restype = ctypes.c_int

user32.OpenClipboard.argtypes = [ctypes.c_void_p]
user32.OpenClipboard.restype = ctypes.c_int

user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = ctypes.c_int

user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = ctypes.c_int

user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
user32.SetClipboardData.restype = ctypes.c_void_p

# 마우스 및 키보드 상수
VK_CONTROL = 0x11
VK_V = 0x56
VK_RETURN = 0x0D
KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
SW_RESTORE = 9
GA_ROOT = 2

GMEM_MOVEABLE = 0x0002
CF_UNICODETEXT = 13


def set_clipboard_text(text):
    """64비트 Windows 완벽 호환 Win32 API 클립보드 복사 함수."""
    for _ in range(10):
        if user32.OpenClipboard(None):
            break
        time.sleep(0.05)
    else:
        return False
    try:
        user32.EmptyClipboard()
        encoded = text.encode("utf-16-le") + b"\x00\x00"
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
        if not h_mem:
            return False
        p_mem = kernel32.GlobalLock(h_mem)
        if not p_mem:
            return False
        ctypes.memmove(p_mem, encoded, len(encoded))
        kernel32.GlobalUnlock(h_mem)
        res = user32.SetClipboardData(CF_UNICODETEXT, h_mem)
        return bool(res)
    finally:
        user32.CloseClipboard()


def get_visible_windows():
    """현재 열려 있는 사용자 창 목록(HWND, 제목)을 반환합니다."""
    windows = []

    def enum_windows_callback(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value.strip()

        if not title or title in ("Program Manager", "Default IME", "MSCTFIME UI", "Settings"):
            return True

        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top

        if width > 100 and height > 100:
            windows.append((hwnd, title))
        return True

    cb = WNDENUMPROC(enum_windows_callback)
    user32.EnumWindows(cb, 0)
    return windows


def force_foreground_window(hwnd):
    """지정된 창을 확실하게 최상단으로 가져옵니다."""
    user32.ShowWindow(hwnd, SW_RESTORE)
    time.sleep(0.15)
    cur_thread = kernel32.GetCurrentThreadId()
    target_thread = user32.GetWindowThreadProcessId(hwnd, None)
    attached = False
    if cur_thread != target_thread:
        attached = user32.AttachThreadInput(cur_thread, target_thread, True)
    try:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(cur_thread, target_thread, False)
    time.sleep(0.35)


def mouse_click_at(x, y):
    """마우스를 특정 화면 좌표로 이동 후 클릭합니다."""
    user32.SetCursorPos(x, y)
    time.sleep(0.1)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.08)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.35)


def send_ctrl_v():
    """Ctrl + V 키 입력을 확실하게 전송합니다."""
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    time.sleep(0.08)
    user32.keybd_event(VK_V, 0, 0, 0)
    time.sleep(0.08)
    user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.08)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.35)


def send_enter_key():
    """Enter 키 입력을 확실하게 전송합니다."""
    user32.keybd_event(VK_RETURN, 0, 0, 0)
    time.sleep(0.08)
    user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.1)


class AutoEnterQueueApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI & 메신저 자동 메시지/프롬프트 전송기 (반복 & 편집 에디션)")
        self.root.geometry("740x940")
        self.root.resizable(False, False)
        self.root.configure(bg="#F1F5F9")

        # 상태 변수
        self.window_list = []
        self.selected_hwnd = None
        self.selected_title = ""
        self.click_rel_x = None
        self.click_rel_y = None

        self.tasks = []
        self.task_counter = 1
        self.is_running = False
        self.editing_task_id = None

        self.setup_ui()
        self.refresh_windows()
        self.update_clock_loop()
        self.start_scheduler_thread()

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=24)

        main_frame = ttk.Frame(self.root, padding="12")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. 상단 타이틀 & 현재 컴퓨터 시각
        top_bar = tk.Frame(main_frame, bg="#F1F5F9")
        top_bar.pack(fill=tk.X, pady=(0, 6))

        title_frame = tk.Frame(top_bar, bg="#F1F5F9")
        title_frame.pack(side=tk.LEFT)
        tk.Label(title_frame, text="🤖 AI & 메신저 자동 메시지 전송기", font=("Segoe UI", 12, "bold"), fg="#0F172A", bg="#F1F5F9").pack(anchor="w")
        tk.Label(title_frame, text="입력창 자동 클릭 ➜ 프롬프트 붙여넣기 ➜ Enter (반복 예약 & 큐 수정 지원)", font=("Segoe UI", 8), fg="#64748B", bg="#F1F5F9").pack(anchor="w")

        clock_frame = tk.Frame(top_bar, bg="#FFFFFF", padx=10, pady=4, relief="solid", bd=1)
        clock_frame.pack(side=tk.RIGHT)
        tk.Label(clock_frame, text="🕒 컴퓨터 현재 시각", font=("Segoe UI", 8, "bold"), bg="#FFFFFF", fg="#475569").pack()
        self.lbl_now = tk.Label(clock_frame, text="--:--:--", font=("Consolas", 14, "bold"), fg="#0284C7", bg="#FFFFFF")
        self.lbl_now.pack()

        # 2. 대상 창 및 입력 위치 지정 카드
        target_card = tk.LabelFrame(main_frame, text=" 1. 대상 창 및 입력 위치 지정 (메신저, 브라우저, 샌드박스 등) ", bg="#FFFFFF", fg="#1E293B", font=("Segoe UI", 9, "bold"), padx=10, pady=6)
        target_card.pack(fill=tk.X, pady=(0, 6))

        combo_frame = tk.Frame(target_card, bg="#FFFFFF")
        combo_frame.pack(fill=tk.X, pady=(0, 4))

        self.window_combo = ttk.Combobox(combo_frame, state="readonly", width=46, font=("Segoe UI", 9))
        self.window_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.window_combo.bind("<<ComboboxSelected>>", self.on_window_selected)

        btn_refresh = tk.Button(combo_frame, text="🔄 새로고침", font=("Segoe UI", 9), bg="#F8FAFC", command=self.refresh_windows)
        btn_refresh.pack(side=tk.RIGHT)

        btn_bar = tk.Frame(target_card, bg="#FFFFFF")
        btn_bar.pack(fill=tk.X, pady=(2, 4))

        self.btn_pick = tk.Button(btn_bar, text="🎯 입력 위치 찍기 (3초 카운트다운)", font=("Segoe UI", 9, "bold"), bg="#E0F2FE", fg="#0369A1", padx=8, pady=3, relief="groove", command=self.start_pick_position)
        self.btn_pick.pack(side=tk.LEFT, padx=(0, 6))

        btn_clear_pos = tk.Button(btn_bar, text="위치 초기화", font=("Segoe UI", 8), bg="#F8FAFC", command=self.clear_position)
        btn_clear_pos.pack(side=tk.LEFT, padx=(0, 8))

        btn_test = tk.Button(btn_bar, text="⚡ 즉시 테스트 (3초 뒤 클릭+붙여넣기+엔터)", font=("Segoe UI", 9), bg="#FEF3C7", fg="#B45309", padx=8, pady=3, relief="groove", command=self.test_full_action)
        btn_test.pack(side=tk.LEFT)

        self.lbl_selected_info = tk.Label(
            target_card,
            text="선택된 창: 없음 | 입력 위치: 미지정 (창 포커스만 유지)",
            bg="#F0FDF4",
            fg="#15803D",
            font=("Segoe UI", 8, "bold"),
            anchor="w",
            padx=8,
            pady=3,
            relief="solid",
            bd=1
        )
        self.lbl_selected_info.pack(fill=tk.X, pady=(2, 0))

        # 3. 프롬프트 & 시작 시간 & 반복 설정 카드
        setting_card = tk.LabelFrame(main_frame, text=" 2. 메시지 내용, 시작 시간 및 반복 설정 ", bg="#FFFFFF", fg="#1E293B", font=("Segoe UI", 9, "bold"), padx=10, pady=6)
        setting_card.pack(fill=tk.X, pady=(0, 6))

        tk.Label(setting_card, text="전송할 메시지 / 프롬프트 (비워두면 Enter만 전송):", font=("Segoe UI", 8, "bold"), bg="#FFFFFF", fg="#475569").pack(anchor="w")

        self.txt_prompt = tk.Text(setting_card, height=2, font=("Segoe UI", 9), wrap=tk.WORD, relief="solid", bd=1)
        self.txt_prompt.pack(fill=tk.X, pady=(2, 4))
        self.txt_prompt.insert("1.0", "다음 작업을 이어서 진행해줘.")

        # 시작 시각 입력 줄
        time_input_row = tk.Frame(setting_card, bg="#FFFFFF")
        time_input_row.pack(fill=tk.X, pady=(0, 4))

        tk.Label(time_input_row, text="시작 시각(컴퓨터 기준)  ", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", fg="#334155").pack(side=tk.LEFT)

        self.sp_hours = tk.Spinbox(time_input_row, from_=0, to=23, width=3, font=("Consolas", 11, "bold"), justify="center", format="%02.0f")
        self.sp_hours.pack(side=tk.LEFT)
        tk.Label(time_input_row, text=" 시  ", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(side=tk.LEFT)

        self.sp_mins = tk.Spinbox(time_input_row, from_=0, to=59, width=3, font=("Consolas", 11, "bold"), justify="center", format="%02.0f")
        self.sp_mins.pack(side=tk.LEFT)
        tk.Label(time_input_row, text=" 분  ", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(side=tk.LEFT)

        self.sp_secs = tk.Spinbox(time_input_row, from_=0, to=59, width=3, font=("Consolas", 11, "bold"), justify="center", format="%02.0f")
        self.sp_secs.pack(side=tk.LEFT)
        tk.Label(time_input_row, text=" 초", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", fg="#334155").pack(side=tk.LEFT)

        quick_frame = tk.Frame(time_input_row, bg="#FFFFFF")
        quick_frame.pack(side=tk.RIGHT)
        for text, delta_m in [("+10분", 10), ("+30분", 30), ("+1시간", 60), ("+2시간", 120)]:
            b = tk.Button(quick_frame, text=text, font=("Segoe UI", 8), bg="#F8FAFC", padx=3, pady=1, command=lambda dm=delta_m: self.quick_set_time(dm))
            b.pack(side=tk.LEFT, padx=1)

        default_target = datetime.datetime.now() + datetime.timedelta(minutes=30)
        self.set_time_inputs(default_target.hour, default_target.minute, 0)

        # ---------------- 반복 실행 옵션 영역 ----------------
        repeat_box = tk.LabelFrame(setting_card, text=" 🔁 주기적 반복 실행 옵션 ", bg="#F8FAFC", fg="#0F172A", font=("Segoe UI", 8, "bold"), padx=8, pady=4)
        repeat_box.pack(fill=tk.X, pady=(4, 6))

        self.chk_repeat = tk.BooleanVar(value=False)
        chk_rep_btn = tk.Checkbutton(
            repeat_box,
            text="이 작업을 주기적으로 반복 실행하기 (메신저 정기 알림 / 주기적 작업)",
            variable=self.chk_repeat,
            bg="#F8FAFC",
            font=("Segoe UI", 9, "bold"),
            fg="#1D4ED8",
            command=self.toggle_repeat_ui
        )
        chk_rep_btn.pack(anchor="w")

        self.frame_repeat_detail = tk.Frame(repeat_box, bg="#F8FAFC")
        self.frame_repeat_detail.pack(fill=tk.X, padx=12, pady=(2, 2))

        row_interval = tk.Frame(self.frame_repeat_detail, bg="#F8FAFC")
        row_interval.pack(anchor="w", pady=(0, 4))
        tk.Label(row_interval, text="반복 주기:  매 ", font=("Segoe UI", 9), bg="#F8FAFC").pack(side=tk.LEFT)
        self.sp_interval = tk.Spinbox(row_interval, from_=1, to=999, width=4, font=("Consolas", 10, "bold"), justify="center")
        self.sp_interval.pack(side=tk.LEFT)
        self.sp_interval.delete(0, "end")
        self.sp_interval.insert(0, "30")

        self.interval_unit_var = tk.StringVar(value="분")
        self.combo_unit = ttk.Combobox(row_interval, textvariable=self.interval_unit_var, values=["분", "시간"], width=4, state="readonly")
        self.combo_unit.pack(side=tk.LEFT, padx=(4, 4))
        tk.Label(row_interval, text="마다 자동 재전송", font=("Segoe UI", 9), bg="#F8FAFC").pack(side=tk.LEFT)

        row_end = tk.Frame(self.frame_repeat_detail, bg="#F8FAFC")
        row_end.pack(anchor="w")

        self.repeat_mode_var = tk.StringVar(value="infinite")

        r_inf = tk.Radiobutton(row_end, text="무한 반복 (중지할 때까지)", variable=self.repeat_mode_var, value="infinite", bg="#F8FAFC", font=("Segoe UI", 8), command=self.update_end_condition_ui)
        r_inf.pack(side=tk.LEFT, padx=(0, 10))

        r_until = tk.Radiobutton(row_end, text="종료 시각:", variable=self.repeat_mode_var, value="until_time", bg="#F8FAFC", font=("Segoe UI", 8), command=self.update_end_condition_ui)
        r_until.pack(side=tk.LEFT)
        self.entry_until = tk.Entry(row_end, width=8, font=("Consolas", 9), justify="center")
        self.entry_until.insert(0, (datetime.datetime.now() + datetime.timedelta(hours=6)).strftime("%H:%M:%S"))
        self.entry_until.pack(side=tk.LEFT, padx=(2, 10))

        r_count = tk.Radiobutton(row_end, text="횟수 제한: 총", variable=self.repeat_mode_var, value="max_count", bg="#F8FAFC", font=("Segoe UI", 8), command=self.update_end_condition_ui)
        r_count.pack(side=tk.LEFT)
        self.sp_max_count = tk.Spinbox(row_end, from_=1, to=9999, width=4, font=("Consolas", 9), justify="center")
        self.sp_max_count.delete(0, "end")
        self.sp_max_count.insert(0, "10")
        self.sp_max_count.pack(side=tk.LEFT, padx=(2, 2))
        tk.Label(row_end, text="회 실행 후 종료", font=("Segoe UI", 8), bg="#F8FAFC").pack(side=tk.LEFT)

        self.toggle_repeat_ui()

        # [➕ 큐에 추가] / [💾 수정 저장] / [취소] 버튼 프레임
        btn_action_card = tk.Frame(setting_card, bg="#FFFFFF")
        btn_action_card.pack(fill=tk.X, pady=(4, 0))

        self.btn_submit_task = tk.Button(
            btn_action_card,
            text="➕ 위 설정(메시지 + 시각 + 반복)을 작업 큐에 추가하기",
            bg="#2563EB",
            fg="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            pady=5,
            relief="flat",
            cursor="hand2",
            command=self.submit_task
        )
        self.btn_submit_task.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.btn_cancel_edit = tk.Button(
            btn_action_card,
            text="수정 취소",
            bg="#94A3B8",
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=5,
            relief="flat",
            command=self.cancel_edit
        )

        # 4. 예약 작업 큐 테이블 (Treeview)
        queue_card = tk.LabelFrame(main_frame, text=" 3. 예약 작업 큐 목록 (더블클릭하여 수정 가능) ", bg="#FFFFFF", fg="#1E293B", font=("Segoe UI", 9, "bold"), padx=8, pady=4)
        queue_card.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        columns = ("id", "time", "remain", "target", "repeat", "prompt", "status")
        self.tree = ttk.Treeview(queue_card, columns=columns, show="headings", height=5)
        self.tree.heading("id", text="순번", anchor="center")
        self.tree.heading("time", text="예약 시각", anchor="center")
        self.tree.heading("remain", text="남은 시간", anchor="center")
        self.tree.heading("target", text="대상 창", anchor="w")
        self.tree.heading("repeat", text="반복 설정", anchor="center")
        self.tree.heading("prompt", text="메시지 / 프롬프트", anchor="w")
        self.tree.heading("status", text="상태", anchor="center")

        self.tree.column("id", width=36, anchor="center")
        self.tree.column("time", width=110, anchor="center")
        self.tree.column("remain", width=80, anchor="center")
        self.tree.column("target", width=130, anchor="w")
        self.tree.column("repeat", width=95, anchor="center")
        self.tree.column("prompt", width=150, anchor="w")
        self.tree.column("status", width=75, anchor="center")

        self.tree.bind("<Double-1>", self.on_tree_double_click)

        tree_scroll = ttk.Scrollbar(queue_card, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=tree_scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 큐 관리 버튼 바
        q_btn_bar = tk.Frame(main_frame, bg="#F1F5F9")
        q_btn_bar.pack(fill=tk.X, pady=(0, 6))

        btn_edit = tk.Button(q_btn_bar, text="✏️ 선택 작업 수정", font=("Segoe UI", 8, "bold"), bg="#E0E7FF", fg="#3730A3", padx=6, pady=2, command=self.start_edit_selected)
        btn_edit.pack(side=tk.LEFT, padx=(0, 6))

        btn_del = tk.Button(q_btn_bar, text="🗑 선택 항목 삭제", font=("Segoe UI", 8), bg="#FEE2E2", fg="#991B1B", padx=6, pady=2, command=self.delete_selected_task)
        btn_del.pack(side=tk.LEFT, padx=(0, 6))

        btn_clear_done = tk.Button(q_btn_bar, text="🧹 완료 항목 정리", font=("Segoe UI", 8), bg="#F8FAFC", padx=6, pady=2, command=self.clear_completed_tasks)
        btn_clear_done.pack(side=tk.LEFT)

        self.chk_beep = tk.BooleanVar(value=True)
        c1 = tk.Checkbutton(q_btn_bar, text="실행 5초 전 경고음", variable=self.chk_beep, bg="#F1F5F9", font=("Segoe UI", 8))
        c1.pack(side=tk.RIGHT)

        # 5. 현재 카운트다운 박스
        status_card = tk.Frame(main_frame, bg="#FFFFFF", bd=1, relief="solid", pady=4)
        status_card.pack(fill=tk.X, pady=(0, 6))

        self.lbl_target_info = tk.Label(status_card, text="큐 실행 대기 중 (작업 추가 후 아래 [▶ 큐 순차 실행 시작] 클릭)", font=("Segoe UI", 8, "bold"), bg="#FFFFFF", fg="#64748B")
        self.lbl_target_info.pack()

        self.lbl_countdown = tk.Label(status_card, text="-- : -- : --", font=("Consolas", 18, "bold"), fg="#2563EB", bg="#FFFFFF")
        self.lbl_countdown.pack(pady=1)

        # 6. 제어 버튼
        ctrl_frame = tk.Frame(main_frame, bg="#F1F5F9")
        ctrl_frame.pack(fill=tk.X, pady=(0, 6))

        self.btn_start = tk.Button(ctrl_frame, text="▶ 큐 순차 실행 시작", bg="#16A34A", fg="#FFFFFF", font=("Segoe UI", 10, "bold"), pady=6, relief="flat", cursor="hand2", command=self.start_queue_processing)
        self.btn_start.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.btn_stop = tk.Button(ctrl_frame, text="⏹ 큐 실행 중지", bg="#CBD5E1", fg="#475569", font=("Segoe UI", 10, "bold"), pady=6, relief="flat", state=tk.DISABLED, command=self.stop_queue_processing)
        self.btn_stop.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(6, 0))

        # 7. 실시간 로그 창
        self.log_text = tk.Text(main_frame, height=4, font=("Consolas", 8), bg="#FFFFFF", fg="#334155", relief="solid", bd=1)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log("프로그램이 시작되었습니다. 작업을 등록하거나 더블클릭하여 수정할 수 있습니다.")

    def log(self, message):
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{now_str}] {message}\n")
        self.log_text.see(tk.END)

    def toggle_repeat_ui(self):
        is_rep = self.chk_repeat.get()
        state = "normal" if is_rep else "disabled"
        self.sp_interval.config(state=state)
        self.combo_unit.config(state="readonly" if is_rep else "disabled")
        self.update_end_condition_ui()

    def update_end_condition_ui(self):
        is_rep = self.chk_repeat.get()
        mode = self.repeat_mode_var.get()
        self.entry_until.config(state="normal" if (is_rep and mode == "until_time") else "disabled")
        self.sp_max_count.config(state="normal" if (is_rep and mode == "max_count") else "disabled")

    def update_clock_loop(self):
        now = datetime.datetime.now()
        self.lbl_now.config(text=now.strftime("%H:%M:%S"))
        self.root.after(500, self.update_clock_loop)

    def set_time_inputs(self, h, m, s):
        self.sp_hours.delete(0, "end")
        self.sp_hours.insert(0, f"{h:02d}")
        self.sp_mins.delete(0, "end")
        self.sp_mins.insert(0, f"{m:02d}")
        self.sp_secs.delete(0, "end")
        self.sp_secs.insert(0, f"{s:02d}")

    def quick_set_time(self, delta_minutes):
        t = datetime.datetime.now() + datetime.timedelta(minutes=delta_minutes)
        self.set_time_inputs(t.hour, t.minute, 0)

    def update_info_label(self):
        t_title = self.selected_title[:35] if self.selected_title else "없음"
        if self.click_rel_x is not None and self.click_rel_y is not None:
            pos_str = f"클릭 좌표: (X:{self.click_rel_x}, Y:{self.click_rel_y})"
        else:
            pos_str = "클릭 좌표: 미지정 (포커스 유지)"
        self.lbl_selected_info.config(text=f"선택 창: {t_title} | {pos_str}")

    def clear_position(self):
        self.click_rel_x = None
        self.click_rel_y = None
        self.update_info_label()
        self.log("입력 클릭 좌표가 초기화되었습니다 (창 포커스만 유지).")

    def refresh_windows(self):
        self.window_list = get_visible_windows()
        titles = [f"{w[1]} (HWND: {hex(w[0])})" for w in self.window_list]
        self.window_combo["values"] = titles

        matched_index = None
        for i, (hwnd, title) in enumerate(self.window_list):
            tl = title.lower()
            if any(k in tl for k in ("sandbox", "샌드박스", "codex", "chatgpt", "카카오톡", "kakao", "discord", "slack")):
                matched_index = i
                break

        if matched_index is not None:
            self.window_combo.current(matched_index)
            self.on_window_selected()
        elif titles:
            self.window_combo.current(0)
            self.on_window_selected()

        self.log(f"창 목록 갱신 ({len(self.window_list)}개 발견)")

    def on_window_selected(self, event=None):
        idx = self.window_combo.current()
        if idx >= 0 and idx < len(self.window_list):
            hwnd, title = self.window_list[idx]
            self.selected_hwnd = hwnd
            self.selected_title = title
            self.update_info_label()

    def start_pick_position(self):
        self.btn_pick.config(state=tk.DISABLED)

        def pick_thread():
            for s in (3, 2, 1):
                self.log(f"3초 안에 입력창(텍스트박스) 부분을 마우스로 가리키거나 클릭하세요! ({s}초 전...)")
                winsound.Beep(1000, 150)
                time.sleep(0.85)

            pt = wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))

            child_hwnd = user32.WindowFromPoint(pt)
            root_hwnd = user32.GetAncestor(child_hwnd, GA_ROOT)
            if not root_hwnd:
                root_hwnd = user32.GetForegroundWindow()

            length = user32.GetWindowTextLengthW(root_hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(root_hwnd, buff, length + 1)
            title = buff.value.strip()

            rect = wintypes.RECT()
            user32.GetWindowRect(root_hwnd, ctypes.byref(rect))
            rel_x = pt.x - rect.left
            rel_y = pt.y - rect.top

            self.root.after(0, lambda: self.finish_pick_position(root_hwnd, title, rel_x, rel_y))

        threading.Thread(target=pick_thread, daemon=True).start()

    def finish_pick_position(self, hwnd, title, rel_x, rel_y):
        self.btn_pick.config(state=tk.NORMAL)
        if hwnd and user32.IsWindow(hwnd):
            self.selected_hwnd = hwnd
            self.selected_title = title if title else "(제목 없음)"
            self.click_rel_x = rel_x
            self.click_rel_y = rel_y
            self.update_info_label()
            self.log(f"입력 위치 캡처 성공! 창: '{self.selected_title[:20]}' | 상대좌표: ({rel_x}, {rel_y})")
            winsound.Beep(1800, 250)
        else:
            self.log("위치 캡처 실패")

    def test_full_action(self):
        if not self.selected_hwnd or not user32.IsWindow(self.selected_hwnd):
            messagebox.showwarning("경고", "먼저 유효한 대상 창을 선택하거나 위치를 찍어주세요.")
            return

        prompt = self.txt_prompt.get("1.0", tk.END).rstrip("\r\n")

        def run_test():
            self.log("[테스트 시작] 3초 후 포커스 ➜ 클릭 ➜ 붙여넣기 ➜ Enter를 실행합니다...")
            time.sleep(3)
            try:
                force_foreground_window(self.selected_hwnd)
                self.log("1. 대상 창 최상단 활성화 완료")

                if self.click_rel_x is not None and self.click_rel_y is not None:
                    rect = wintypes.RECT()
                    user32.GetWindowRect(self.selected_hwnd, ctypes.byref(rect))
                    cx = rect.left + self.click_rel_x
                    cy = rect.top + self.click_rel_y
                    mouse_click_at(cx, cy)
                    self.log(f"2. 입력 영역 마우스 클릭 완료 ({cx}, {cy})")
                else:
                    self.log("2. 지정 좌표 없음 (기존 커서 포커스 유지)")

                if prompt:
                    ok = set_clipboard_text(prompt)
                    if not ok:
                        self.root.clipboard_clear()
                        self.root.clipboard_append(prompt)
                        self.root.update()
                    self.log(f"3. 클립보드 복사 완료 ({len(prompt)}자)")
                    time.sleep(0.15)
                    send_ctrl_v()
                    self.log("4. Ctrl+V 키 전송 완료")
                else:
                    self.log("3. 메시지가 비어 있어 텍스트 입력은 건너뜁니다.")

                send_enter_key()
                self.log("5. Enter 키 전송 완료")
                self.log(">>> [테스트 완료] 모든 과정이 정상 작동합니다!")
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception as e:
                self.log(f"[테스트 에러] {str(e)}")

        threading.Thread(target=run_test, daemon=True).start()

    def submit_task(self):
        """작업 추가 또는 수정 완료를 처리합니다."""
        if not self.selected_hwnd or not user32.IsWindow(self.selected_hwnd):
            messagebox.showwarning("경고", "먼저 대상 창을 선택해주세요.")
            return

        try:
            h = int(self.sp_hours.get())
            m = int(self.sp_mins.get())
            s = int(self.sp_secs.get())
            if not (0 <= h <= 23 and 0 <= m <= 59 and 0 <= s <= 59):
                raise ValueError
        except ValueError:
            messagebox.showerror("입력 오류", "시, 분, 초를 올바르게 입력해주세요.")
            return

        prompt = self.txt_prompt.get("1.0", tk.END).rstrip("\r\n")

        now = datetime.datetime.now()
        target = now.replace(hour=h, minute=m, second=s, microsecond=0)
        if target <= now:
            target += datetime.timedelta(days=1)
            time_display = f"내일 {target.strftime('%H:%M:%S')}"
        else:
            time_display = f"오늘 {target.strftime('%H:%M:%S')}"

        # 반복 옵션 파싱
        is_repeat = self.chk_repeat.get()
        interval_val = 30
        interval_unit = "분"
        interval_minutes = 30
        repeat_mode = "infinite"
        until_time = None
        max_count = None

        if is_repeat:
            try:
                interval_val = int(self.sp_interval.get())
                if interval_val <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("입력 오류", "반복 주기는 1 이상의 숫자로 입력해주세요.")
                return

            interval_unit = self.interval_unit_var.get()
            interval_minutes = interval_val if interval_unit == "분" else (interval_val * 60)
            repeat_mode = self.repeat_mode_var.get()

            if repeat_mode == "until_time":
                time_str = self.entry_until.get().strip()
                try:
                    parts = [int(p) for p in time_str.split(":")]
                    if len(parts) == 2:
                        uh, um = parts
                        us = 0
                    elif len(parts) == 3:
                        uh, um, us = parts
                    else:
                        raise ValueError
                    until_today = now.replace(hour=uh, minute=um, second=us, microsecond=0)
                    if until_today <= target:
                        until_time = until_today + datetime.timedelta(days=1)
                    else:
                        until_time = until_today
                except Exception:
                    messagebox.showerror("입력 오류", "종료 시각 형식이 올바르지 않습니다 (예: 18:00:00).")
                    return
            elif repeat_mode == "max_count":
                try:
                    max_count = int(self.sp_max_count.get())
                    if max_count <= 0:
                        raise ValueError
                except ValueError:
                    messagebox.showerror("입력 오류", "반복 횟수는 1 이상의 숫자로 입력해주세요.")
                    return

        # 반복 표시 문자열
        if not is_repeat:
            repeat_display = "1회성"
        else:
            unit_str = f"매 {interval_val}{interval_unit}"
            if repeat_mode == "infinite":
                repeat_display = f"{unit_str} (무한)"
            elif repeat_mode == "until_time":
                repeat_display = f"{unit_str} (~{until_time.strftime('%H:%M')})"
            else:
                repeat_display = f"{unit_str} (총 {max_count}회)"

        if self.editing_task_id is not None:
            task = next((t for t in self.tasks if t["id"] == self.editing_task_id), None)
            if task:
                task["target_time"] = target
                task["time_display"] = time_display
                task["hwnd"] = self.selected_hwnd
                task["title"] = self.selected_title
                task["prompt"] = prompt
                task["rel_x"] = self.click_rel_x
                task["rel_y"] = self.click_rel_y
                task["is_repeat"] = is_repeat
                task["interval_val"] = interval_val
                task["interval_unit"] = interval_unit
                task["interval_minutes"] = interval_minutes
                task["repeat_mode"] = repeat_mode
                task["until_time"] = until_time
                task["max_count"] = max_count
                task["repeat_display"] = repeat_display
                task["status"] = "대기 중"
                self.log(f"✏️ [작업 #{task['id']} 수정 완료] 시각: {time_display} | 반복: {repeat_display}")
            self.cancel_edit()
        else:
            task = {
                "id": self.task_counter,
                "target_time": target,
                "time_display": time_display,
                "hwnd": self.selected_hwnd,
                "title": self.selected_title,
                "prompt": prompt,
                "rel_x": self.click_rel_x,
                "rel_y": self.click_rel_y,
                "is_repeat": is_repeat,
                "interval_val": interval_val,
                "interval_unit": interval_unit,
                "interval_minutes": interval_minutes,
                "repeat_mode": repeat_mode,
                "until_time": until_time,
                "max_count": max_count,
                "repeat_display": repeat_display,
                "run_count": 0,
                "status": "대기 중"
            }
            self.task_counter += 1
            self.tasks.append(task)
            self.log(f"➕ [작업 #{task['id']} 등록] ({time_display}) | 반복: {repeat_display}")

            next_suggest = target + datetime.timedelta(minutes=interval_minutes if is_repeat else 60)
            self.set_time_inputs(next_suggest.hour, next_suggest.minute, 0)

        self.tasks.sort(key=lambda t: t["target_time"])
        self.update_treeview()

    def start_edit_selected(self):
        """선택된 작업을 수정 모드로 불러옵니다."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("안내", "수정할 작업을 목록에서 선택해주세요.")
            return

        t_id = int(selected[0])
        task = next((t for t in self.tasks if t["id"] == t_id), None)
        if not task:
            return

        self.editing_task_id = t_id

        self.selected_hwnd = task["hwnd"]
        self.selected_title = task["title"]
        self.click_rel_x = task["rel_x"]
        self.click_rel_y = task["rel_y"]
        self.update_info_label()

        for i, (hwnd, title) in enumerate(self.window_list):
            if hwnd == task["hwnd"]:
                self.window_combo.current(i)
                break

        t_time = task["target_time"]
        self.set_time_inputs(t_time.hour, t_time.minute, t_time.second)

        self.txt_prompt.delete("1.0", tk.END)
        self.txt_prompt.insert("1.0", task.get("prompt", ""))

        is_rep = task.get("is_repeat", False)
        self.chk_repeat.set(is_rep)
        if is_rep:
            self.sp_interval.delete(0, "end")
            self.sp_interval.insert(0, str(task.get("interval_val", 30)))
            self.interval_unit_var.set(task.get("interval_unit", "분"))
            self.repeat_mode_var.set(task.get("repeat_mode", "infinite"))
            if task.get("until_time"):
                self.entry_until.delete(0, "end")
                self.entry_until.insert(0, task["until_time"].strftime("%H:%M:%S"))
            if task.get("max_count"):
                self.sp_max_count.delete(0, "end")
                self.sp_max_count.insert(0, str(task["max_count"]))
        self.toggle_repeat_ui()

        self.btn_submit_task.config(text=f"💾 [#{t_id}번 작업] 수정 내용 저장하기", bg="#4F46E5")
        self.btn_cancel_edit.pack(side=tk.RIGHT, padx=(6, 0))
        self.log(f"✏️ [#{t_id}번 작업] 편집 모드 활성화 (내용 수정 후 [수정 내용 저장하기] 클릭)")

    def on_tree_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.start_edit_selected()

    def cancel_edit(self):
        self.editing_task_id = None
        self.btn_submit_task.config(text="➕ 위 설정(메시지 + 시각 + 반복)을 작업 큐에 추가하기", bg="#2563EB")
        self.btn_cancel_edit.pack_forget()
        self.log("작업 수정 모드가 취소되었습니다.")

    def update_treeview(self):
        now = datetime.datetime.now()

        existing_iids = set(self.tree.get_children())
        current_iids = set(str(t["id"]) for t in self.tasks)

        for old_iid in existing_iids - current_iids:
            self.tree.delete(old_iid)

        for idx, t in enumerate(self.tasks):
            t_id = str(t["id"])
            diff = (t["target_time"] - now).total_seconds()
            if t["status"] == "대기 중":
                if diff > 0:
                    hours = int(diff // 3600)
                    mins = int((diff % 3600) // 60)
                    secs = int(diff % 60)
                    remain_str = f"{hours:02d}:{mins:02d}:{secs:02d}"
                else:
                    remain_str = "도달함"
            else:
                remain_str = "-"

            p_preview = t["prompt"][:18].replace("\n", " ") + "..." if len(t["prompt"]) > 18 else (t["prompt"].replace("\n", " ") if t["prompt"] else "(엔터만)")
            rep_str = t.get("repeat_display", "1회성")
            status_str = t["status"]
            if t.get("is_repeat") and t.get("run_count", 0) > 0 and t["status"] == "대기 중":
                status_str = f"반복중({t['run_count']}회)"

            vals = (f"#{t['id']}", t["time_display"], remain_str, t["title"][:18], rep_str, p_preview, status_str)

            if self.tree.exists(t_id):
                self.tree.item(t_id, values=vals)
            else:
                self.tree.insert("", tk.END, iid=t_id, values=vals)

            self.tree.move(t_id, "", idx)

    def delete_selected_task(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("안내", "삭제할 작업을 목록에서 선택해주세요.")
            return
        for item_id in selected:
            t_id = int(item_id)
            self.tasks = [t for t in self.tasks if t["id"] != t_id]
            if self.editing_task_id == t_id:
                self.cancel_edit()
        self.update_treeview()
        self.log("선택한 작업이 큐에서 삭제되었습니다.")

    def clear_completed_tasks(self):
        self.tasks = [t for t in self.tasks if t["status"] == "대기 중"]
        self.update_treeview()
        self.log("완료된 작업 항목이 정리되었습니다.")

    def start_queue_processing(self):
        pending_count = sum(1 for t in self.tasks if t["status"] == "대기 중")
        if pending_count == 0:
            messagebox.showwarning("안내", "큐에 '대기 중'인 작업이 없습니다.")
            return

        self.is_running = True
        self.btn_start.config(state=tk.DISABLED, bg="#94A3B8")
        self.btn_stop.config(state=tk.NORMAL, bg="#DC2626", fg="#FFFFFF", cursor="hand2")
        self.log(f"큐 순차 실행 시작! (대기 작업 {pending_count}개)")

    def stop_queue_processing(self):
        self.is_running = False
        self.btn_start.config(state=tk.NORMAL, bg="#16A34A")
        self.btn_stop.config(state=tk.DISABLED, bg="#CBD5E1", fg="#475569")
        self.lbl_target_info.config(text="큐 실행이 중지되었습니다.", fg="#64748B")
        self.lbl_countdown.config(text="-- : -- : --")
        self.log("큐 실행이 중지되었습니다.")

    def start_scheduler_thread(self):
        def loop():
            warned_task_id = None

            while True:
                now = datetime.datetime.now()
                self.root.after(0, self.update_treeview)

                if self.is_running:
                    pending_tasks = [t for t in self.tasks if t["status"] == "대기 중"]

                    if not pending_tasks:
                        self.root.after(0, self.on_all_tasks_completed)
                        time.sleep(1)
                        continue

                    current_task = pending_tasks[0]
                    diff = (current_task["target_time"] - now).total_seconds()

                    if 0 < diff <= 5.5 and warned_task_id != current_task["id"] and self.chk_beep.get():
                        warned_task_id = current_task["id"]
                        threading.Thread(target=lambda: winsound.Beep(1200, 300), daemon=True).start()

                    if diff <= 0:
                        self.root.after(0, lambda t=current_task: self.execute_task(t))
                        time.sleep(2)
                    else:
                        hours = int(diff // 3600)
                        mins = int((diff % 3600) // 60)
                        secs = int(diff % 60)
                        time_str = f"{hours:02d} : {mins:02d} : {secs:02d}"
                        info_str = f"다음 실행: [#{current_task['id']}] {current_task['time_display']} - {current_task['title'][:18]}"

                        self.root.after(0, lambda s=time_str, i=info_str: (
                            self.lbl_countdown.config(text=s),
                            self.lbl_target_info.config(text=i, fg="#1D4ED8")
                        ))

                time.sleep(0.5)

        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def execute_task(self, task):
        task["status"] = "진행 중"
        self.update_treeview()
        self.log(f"⏰ [작업 #{task['id']} 실행] 창 활성화 및 메시지 전송 시작...")

        try:
            hwnd = task["hwnd"]
            if not user32.IsWindow(hwnd):
                task["status"] = "창 닫힘"
                self.log(f"❌ [작업 #{task['id']} 실패] 대상 창이 닫혀 있습니다.")
                self.update_treeview()
                return

            force_foreground_window(hwnd)

            if task["rel_x"] is not None and task["rel_y"] is not None:
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                cx = rect.left + task["rel_x"]
                cy = rect.top + task["rel_y"]
                mouse_click_at(cx, cy)
                self.log(f"   입력 영역 마우스 클릭 완료 ({cx}, {cy})")

            prompt = task.get("prompt", "").strip()
            if prompt:
                ok = set_clipboard_text(prompt)
                if not ok:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(prompt)
                    self.root.update()
                time.sleep(0.15)
                send_ctrl_v()
                self.log(f"   메시지 내용 붙여넣기 완료 ({len(prompt)}자)")

            send_enter_key()
            task["run_count"] = task.get("run_count", 0) + 1
            self.log(f"✅ [작업 #{task['id']} 전송 성공] (총 {task['run_count']}회 완료)")
            if self.chk_beep.get():
                winsound.MessageBeep(winsound.MB_ICONASTERISK)

            # 반복 처리 로직
            if task.get("is_repeat"):
                rep_mode = task.get("repeat_mode", "infinite")
                max_cnt = task.get("max_count")
                until_t = task.get("until_time")
                interval_m = task.get("interval_minutes", 30)

                should_continue = True
                if rep_mode == "max_count" and task["run_count"] >= max_cnt:
                    should_continue = False
                    task["status"] = f"✅ 완료 ({task['run_count']}회)"
                    self.log(f"🏁 [작업 #{task['id']} 반복 종료] 목표 횟수({max_cnt}회) 달성!")

                if rep_mode == "until_time":
                    next_t = task["target_time"] + datetime.timedelta(minutes=interval_m)
                    if next_t > until_t:
                        should_continue = False
                        task["status"] = f"✅ 종료 (~{until_t.strftime('%H:%M')})"
                        self.log(f"🏁 [작업 #{task['id']} 반복 종료] 지정 종료 시각 도달!")

                if should_continue:
                    next_t = task["target_time"] + datetime.timedelta(minutes=interval_m)
                    task["target_time"] = next_t
                    now = datetime.datetime.now()
                    if next_t.date() > now.date():
                        task["time_display"] = f"내일 {next_t.strftime('%H:%M:%S')}"
                    else:
                        task["time_display"] = f"오늘 {next_t.strftime('%H:%M:%S')}"
                    task["status"] = "대기 중"
                    self.log(f"🔁 [작업 #{task['id']} 자동 재예약] 다음 회차: {task['time_display']}")
                    self.tasks.sort(key=lambda t: t["target_time"])
            else:
                task["status"] = "✅ 완료"

        except Exception as e:
            task["status"] = "오류"
            self.log(f"❌ [작업 #{task['id']} 에러] {str(e)}")
        finally:
            self.update_treeview()

    def on_all_tasks_completed(self):
        self.is_running = False
        self.btn_start.config(state=tk.NORMAL, bg="#16A34A")
        self.btn_stop.config(state=tk.DISABLED, bg="#CBD5E1", fg="#475569")
        self.lbl_target_info.config(text="🎉 모든 큐 예약 작업이 완료되었습니다!", fg="#15803D")
        self.lbl_countdown.config(text="00 : 00 : 00")
        self.log("🎉 등록된 모든 큐 작업 처리가 완료되었습니다!")
        if self.chk_beep.get():
            winsound.MessageBeep(winsound.MB_ICONASTERISK)


if __name__ == "__main__":
    root = tk.Tk()
    app = AutoEnterQueueApp(root)
    root.mainloop()
