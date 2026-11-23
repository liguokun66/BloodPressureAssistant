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
