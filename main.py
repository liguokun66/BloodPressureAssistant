# -*- coding: utf-8 -*-
"""
血压记录助手 · 深色极简风
入口文件
"""

import os
import json

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, NoTransition
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.utils import platform

import theme
import icons
import kbdbg
from theme import C
from widgets import BottomNav
from screens import (HomeScreen, AnalysisScreen, KnowledgeScreen,
                     ArticleScreen, ProfileScreen, AddScreen)
from db import BPDB


FONT_FILES = [
    'NotoSansSC-Regular.otf',
    'NotoSansSC-Regular.ttf',
    'SimHei.ttf',
    'DroidSansFallback.ttf',
    'SourceHanSansSC-Regular.otf',
]


def _imm_show_soft_input():
    """绕过 SDL，直接用 Android InputMethodManager 弹软键盘（兜底）。

    部分机型上 SDL_IsScreenKeyboardShown 恒为 false / SDL 的 showSoftInput
    不生效，导致 Kivy 刚请求键盘就被 release。这里从 Java 层直接要输入法。
    结果写入 kbdbg.KB['imm']：1 成功调用 / 0 返回 false / 字符串为异常。
    """
    try:
        from jnius import autoclass, PythonJavaClass, java_method
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Context = autoclass('android.content.Context')
        activity = PythonActivity.mActivity

        if activity is None:
            kbdbg.KB['imm'] = 0
            return

        class _Task(PythonJavaClass):
            __javainterfaces__ = ['java/lang/Runnable']

            def __init__(self):
                super().__init__()

            @java_method('()V')
            def run(self):
                try:
                    imm = activity.getSystemService(
                        Context.INPUT_METHOD_SERVICE)
                    view = activity.getWindow().getDecorView()
                    kbdbg.KB['imm'] = 1 if imm.showSoftInput(view, 0) else 0
                except Exception as e:
                    kbdbg.KB['imm'] = '%s' % type(e).__name__

        activity.runOnUiThread(_Task())
    except Exception as e:
        kbdbg.KB['imm'] = '%s' % type(e).__name__


def patch_android_keyboard():
    """安卓软键盘补丁（对应真机问题「点输入框键盘不弹出」）。

    现象：输入框 focus 正常，但系统输入法不出来。
    根因（Kivy 2.2.1 window_sdl2.py）：request_keyboard 后每 0.2s 检查
    `is_keyboard_shown()`，为 false 就立刻 release 键盘；部分机型该接口
    始终返回 false，于是键盘永远被关掉。

    做法：
    1) 打补丁后的 _check_keyboard_shown **永不自动 release**（失焦走正常
       release_keyboard 路径）；
    2) 请求键盘后 3s 内每 0.5s 重新 show_keyboard 一次（应对偶发失败）；
    3) 同时用 pyjnius 直接调 InputMethodManager.showSoftInput 兜底；
    状态写进 kbdbg.KB 供界面 DBG 行读取。
    """
    try:
        import time
        from kivy.clock import Clock
        from kivy.base import EventLoop
        cls = type(EventLoop.window)
        if getattr(cls, '_bp_patched', False):
            return

        _orig_req = cls.request_keyboard

        def request_keyboard(self, callback, target, input_type='text',
                             keyboard_suggestions=True):
            kbdbg.KB['req'] += 1
            kbdbg.KB['shown'] = -1
            kbdbg.KB['t'] = time.time()
            kbdbg.KB['retry'] = False
            kbdbg.KB['imm'] = '-'
            res = _orig_req(self, callback, target, input_type,
                            keyboard_suggestions)
            kbdbg.KB['retry'] = True
            # 3s 内每 0.5s 重试一次（SDL + IMM 双通道）
            Clock.schedule_interval(lambda dt: _kb_retry(self), 0.5)
            return res

        def _kb_retry(win):
            n = kbdbg.KB.get('n', 0) + 1
            kbdbg.KB['n'] = n
            if n > 6:
                return False
            try:
                win._win.show_keyboard(win._system_keyboard,
                                      win.softinput_mode, 'text', True)
            except Exception as e:
                kbdbg.KB['err'] = '%s: %s' % (type(e).__name__, e)
            _imm_show_soft_input()
            return True

        def _check_keyboard_shown(self, dt):
            if self._sdl_keyboard is None:
                return False
            try:
                shown = bool(self._win.is_keyboard_shown())
            except Exception:
                return False
            kbdbg.KB['shown'] = 1 if shown else 0
            # 关键：不再因为 SDL 误判而 release 键盘
            return False

        cls.request_keyboard = request_keyboard
        cls._check_keyboard_shown = _check_keyboard_shown
        cls._bp_patched = True
    except Exception as e:
        kbdbg.KB['err'] = 'patch: %s: %s' % (type(e).__name__, e)


def register_chinese_font():
    """注册中文字体，保证中文正常显示"""
    roots = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets'),
        os.path.join(os.getcwd(), 'assets'),
    ]
    for root in roots:
        for name in FONT_FILES:
            p = os.path.join(root, name)
            if os.path.exists(p):
                try:
                    LabelBase.register('NotoSansSC', p)
                    theme.set_font('NotoSansSC')
                    return p
                except Exception as e:
                    print('[font] register failed:', name, e)
    print('[font] 未找到中文字体，请将字体放入 assets/ 目录')
    return None


class Root(BoxLayout):
    """根布局：页面管理器 + 底部导航"""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.app = app
        self.build_ui()

    def build_ui(self):
        self.clear_widgets()
        sm = ScreenManager(transition=NoTransition())
        sm.add_widget(HomeScreen(self.app, name='home'))
        sm.add_widget(AnalysisScreen(self.app, name='analysis'))
        sm.add_widget(KnowledgeScreen(self.app, name='knowledge'))
        sm.add_widget(ArticleScreen(self.app, name='article'))
        sm.add_widget(ProfileScreen(self.app, name='profile'))
        sm.add_widget(AddScreen(self.app, name='add'))
        self.sm = sm
        self.add_widget(sm)
        self.nav = BottomNav(self.app)
        self.add_widget(self.nav)


class BPMain(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = '血压记录助手'
        self.editing_id = None
        self.article_index = 0
        self.prefs_path = os.path.join(self.user_data_dir, 'prefs.json')
        self.dark = self._load_prefs()
        theme.set_dark(self.dark)
        self.db = BPDB(os.path.join(self.user_data_dir, 'bp.db'))

    # ---------------- 偏好 ----------------
    def _load_prefs(self):
        try:
            with open(self.prefs_path, 'r', encoding='utf-8') as f:
                return bool(json.load(f).get('dark', True))
        except Exception:
            return True

    def _save_prefs(self):
        try:
            with open(self.prefs_path, 'w', encoding='utf-8') as f:
                json.dump({'dark': bool(self.dark)}, f)
        except Exception:
            pass

    # ---------------- 构建 ----------------
    def build(self):
        Window.clearcolor = C(theme.BG)
        # 桌面端默认使用手机竖屏尺寸（Android 为全屏，不受影响）
        if platform != 'android':
            Window.size = (430, 860)
        if platform == 'android':
            patch_android_keyboard()
        register_chinese_font()
        icons.register()
        root = Root(self)
        self.root_widget = root
        self.sm = root.sm
        self.nav = root.nav
        self.goto('home')
        return root

    def goto(self, name):
        self.sm.current = name
        if self.nav:
            self.nav.highlight(name)

    def open_article(self, idx):
        self.article_index = idx
        self.goto('article')

    # ---------------- 主题切换 ----------------
    def toggle_theme(self, dark):
        self.dark = bool(dark)
        theme.set_dark(self.dark)
        self._save_prefs()
        Window.clearcolor = C(theme.BG)
        cur = self.sm.current
        if cur in ('add', 'article'):
            cur = 'home'
        root = self.root_widget
        root.build_ui()
        self.sm = root.sm
        self.nav = root.nav
        self.goto(cur)

    # ---------------- 生命周期 ----------------
    def on_start(self):
        try:
            from kivy.base import EventLoop
            EventLoop.window.bind(on_keyboard=self._on_keyboard)
        except Exception:
            pass

    def _on_keyboard(self, window, key, *args):
        # Android 返回键 / ESC
        if key == 27:
            cur = self.sm.current
            if cur == 'add':
                self.goto('home')
                return True
            if cur == 'article':
                self.goto('knowledge')
                return True
            if cur != 'home':
                self.goto('home')
                return True
        return False

    def on_stop(self):
        try:
            self.db.close()
        except Exception:
            pass


if __name__ == '__main__':
    BPMain().run()
