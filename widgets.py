# -*- coding: utf-8 -*-
"""
通用 UI 组件（深色极简主题）
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, RoundedRectangle, Line, Rectangle, Ellipse
from kivy.metrics import dp, sp
from kivy.clock import Clock

import theme
import icons
from theme import C


# ---------------- 文本 ----------------
def L(text, size=14, color=None, bold=False, align='left',
      valign='middle', markup=False, shorten=False,
      size_hint=None, width=None, height=None):
    lbl = Label(
        text=text, font_size=sp(size),
        color=C(color if color is not None else theme.TEXT),
        bold=bold, halign=align, valign=valign, markup=markup,
        font_name=theme.font(), shorten=shorten,
    )
    lbl.size_hint = size_hint if size_hint is not None else (None, None)
    if width is not None:
        lbl.width = dp(width)
    if height is not None:
        lbl.height = dp(height)

    def _sz(inst, val):
        if width is None:
            inst.width = val[0]
        inst.height = val[1]
        if width is not None:
            inst.text_size = (inst.width, None)

    lbl.bind(texture_size=_sz)
    return lbl


# ---------------- 按钮 ----------------
class _LPButton(Button):
    """支持长按的按钮（on_long_press）"""

    def __init__(self, on_long_press=None, long_delay=0.55, **kwargs):
        self._lp_cb = on_long_press
        self._lp_delay = long_delay
        self._lp_timer = None
        self._lp_down = False
        self._lp_fired = False
        if on_long_press is not None:
            self.register_event_type('on_long_press')
            self.bind(on_long_press=on_long_press)
        super().__init__(**kwargs)

    def on_touch_down(self, touch):
        """带长按的按钮：按下不立即触发 on_press（否则一跳走就长按不了），
        等松手再触发；若中途计时器先到期则只触发长按。"""
        if self._lp_cb is None:
            return super().on_touch_down(touch)
        if self.disabled or not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        self._lp_down = True
        self._lp_fired = False
        self.state = 'down'
        self._lp_timer = Clock.schedule_once(self._lp_fire, self._lp_delay)
        return True

    def on_touch_up(self, touch):
        if self._lp_cb is None:
            return super().on_touch_up(touch)
        if not self._lp_down:
            return super().on_touch_up(touch)
        self._lp_down = False
        if self._lp_timer is not None:
            self._lp_timer.cancel()
            self._lp_timer = None
        self.state = 'normal'
        if self._lp_fired:
            # 已作为长按处理，松手不再触发单击（避免误跳转）
            self._lp_fired = False
            return True
        if self.collide_point(*touch.pos):
            self.dispatch('on_press')
            self.dispatch('on_release')
        return True

    def _lp_fire(self, dt):
        self._lp_timer = None
        self._lp_fired = True
        self.state = 'down'
        self.dispatch('on_long_press')

    def on_long_press(self):
        pass


def B(text, bg=None, color=None, size=15, height=46, radius=10,
      bold=False, on_press=None, on_long_press=None, size_hint_y=None,
      width=None, size_hint_x=None, opacity=None, long_delay=0.55,
      markup=False, font_name=None):
    bg = bg if bg is not None else theme.PRIMARY
    kwargs = dict(
        text=text, font_size=sp(size), bold=bold,
        font_name=font_name or theme.font(),
        markup=markup,
        size_hint_y=size_hint_y, height=dp(height),
        background_normal='', background_down='', background_color=(0, 0, 0, 0),
        color=C(color if color is not None else '#FFFFFF'),
    )
    if size_hint_x is not None:
        kwargs['size_hint_x'] = size_hint_x
    if width is not None:
        kwargs['width'] = dp(width)
    btn = _LPButton(on_long_press=on_long_press, long_delay=long_delay,
                    **kwargs)
    with btn.canvas.before:
        btn._ci = Color(rgba=C(bg))
        btn._bg = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(radius)])

    def _upd(*a):
        btn._bg.pos = btn.pos
        btn._bg.size = btn.size

    btn.bind(pos=_upd, size=_upd)
    if opacity is not None:
        btn.opacity = opacity
    if on_press:
        btn.bind(on_press=on_press)
    return btn


# ---------------- 卡片 ----------------
class Card(BoxLayout):
    def __init__(self, radius=14, shadow=True, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = [dp(14), dp(13)]
        self.spacing = dp(10)
        self.size_hint_y = None
        self._shades = []
        with self.canvas.before:
            if shadow:
                dark = theme.is_dark()
                for off, a in ((dp(4), 0.10), (dp(2), 0.14), (dp(1), 0.18)):
                    Color(rgba=(0, 0, 0, a if dark else a * 0.7))
                    r = RoundedRectangle(pos=self.pos, size=self.size,
                                         radius=[dp(radius)])
                    self._shades.append((r, off))
            Color(rgba=C(theme.CARD))
            self._bg = RoundedRectangle(pos=self.pos, size=self.size,
                                        radius=[dp(radius)])
        self.bind(pos=self._upd, size=self._upd)
        self.bind(minimum_height=lambda inst, val: setattr(inst, 'height', val))

    def _upd(self, *a):
        for r, off in self._shades:
            r.pos = (self.x, self.y - off)
            r.size = self.size
        self._bg.pos = self.pos
        self._bg.size = self.size


# ---------------- 顶栏 ----------------
class TopBar(BoxLayout):
    def __init__(self, title='', show_back=False, on_back=None,
                 right_text=None, on_right=None, subtitle=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(56)
        self.padding = [dp(6), dp(8)]
        self.spacing = dp(4)
        with self.canvas.before:
            Color(rgba=C(theme.BG2))
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(rgba=C(theme.DIVIDER))
            self._ln = Line(points=[0, 0, 0, 0], width=1)
        self.bind(pos=self._upd, size=self._upd)
        if show_back:
            self.add_widget(B('‹ 返回', bg=(0, 0, 0, 0), color=theme.TEXT_LIGHT,
                              size=14, height=40, radius=8,
                              on_press=lambda i: on_back and on_back()))
        box = BoxLayout(orientation='vertical', size_hint_x=1,
                        padding=[dp(2), 0])
        self.title_lbl = L(title, 18, theme.TEXT, bold=True, valign='bottom')
        box.add_widget(self.title_lbl)
        if subtitle:
            box.add_widget(L(subtitle, 11, theme.TEXT_LIGHT, valign='top'))
        self.add_widget(box)
        if right_text:
            self.add_widget(B(right_text, bg=(0, 0, 0, 0), color=theme.PRIMARY,
                              size=14, height=40, radius=8,
                              on_press=lambda i: on_right and on_right()))

    def _upd(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._ln.points = [self.x, self.y, self.x + self.width, self.y]


# ---------------- 输入框 ----------------
class FieldInput(TextInput):
    def __init__(self, **kwargs):
        kwargs.setdefault('background_normal', '')
        kwargs.setdefault('background_active', '')
        kwargs.setdefault('background_color', (0, 0, 0, 0))
        kwargs.setdefault('font_name', theme.font())
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(rgba=C(theme.ACCENT))
            self._bg = RoundedRectangle(pos=self.pos, size=self.size,
                                        radius=[dp(10)])
            self._bdc = Color(rgba=C(theme.DIVIDER))
            self._bd = Line(rectangle=(self.x, self.y, self.width, self.height),
                            width=1.0)
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._bd.rectangle = (self.x, self.y, self.width, self.height)

    def set_border(self, color):
        """异常高亮：改变输入框描边颜色"""
        self._bdc.rgba = C(color)


def TI(hint='', text='', size=15, input_type='number', multiline=False,
       readonly=False, height=48, fg=None):
    return FieldInput(
        hint_text=hint, text=text, font_size=sp(size), input_type=input_type,
        multiline=multiline, readonly=readonly,
        size_hint_y=None, height=dp(height),
        foreground_color=C(fg if fg is not None else theme.TEXT),
        hint_text_color=C(theme.TEXT_LIGHT),
        cursor_color=C(theme.PRIMARY),
        padding=[dp(12), dp(13)],
    )


# ---------------- 底部导航 ----------------
class BottomNav(BoxLayout):
    TABS = [
        ('记录', 'home', 'record'),
        ('分析', 'analysis', 'chart'),
        ('知识', 'knowledge', 'book'),
        ('我的', 'profile', 'user'),
    ]

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.size_hint_y = None
        self.height = dp(64)
        self.padding = [dp(6), dp(7)]
        self.spacing = dp(2)
        with self.canvas.before:
            Color(rgba=C(theme.NAV_BG))
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(rgba=C(theme.DIVIDER))
            self._line = Line(points=[0, 0, 0, 0], width=1)
        self.bind(pos=self._upd, size=self._upd)
        self.buttons = {}
        for label, name, icon in self.TABS:
            btn = Button(
                text='[font=%s]%s[/font]\n%s' % (icons.FONT_NAME, icons.ic(icon),
                                                label),
                font_size=sp(11), font_name=theme.font(),
                markup=True,
                background_normal='', background_down='',
                background_color=(0, 0, 0, 0),
                color=C(theme.TEXT_LIGHT),
            )
            btn.bind(on_press=lambda inst, n=name: self.switch(n))
            self.add_widget(btn)
            self.buttons[name] = btn
        self.highlight('home')

    def _upd(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._line.points = [self.x, self.y + self.height,
                             self.x + self.width, self.y + self.height]

    def switch(self, name):
        # add 页面属于「记录」标签
        tab = 'home' if name == 'add' else name
        self.app.sm.current = name
        self.highlight(tab)

    def highlight(self, name):
        tab = 'home' if name == 'add' else name
        for n, btn in self.buttons.items():
            btn.color = C(theme.PRIMARY if n == tab else theme.TEXT_LIGHT)
            btn.bold = (n == tab)


# ---------------- 血压柱状图（柱体：低压 → 高压）----------------
class BarChart(FloatLayout):
    def __init__(self, **kwargs):
        kwargs.setdefault('size_hint', (None, None))
        kwargs.setdefault('height', dp(190))
        super().__init__(**kwargs)
        self.records = []
        self.ymin, self.ymax = 40, 200
        self._lbls = []
        with self.canvas.before:
            Color(rgba=C(theme.CARD))
            self._bg = RoundedRectangle(pos=self.pos, size=self.size,
                                        radius=[dp(14)])
        self.bind(pos=self._on_geom, size=self._on_geom)

    def _on_geom(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self.redraw()

    def set_data(self, records):
        self.records = list(records or [])
        self.redraw()

    def redraw(self, *a):
        for lb in self._lbls:
            try:
                self.remove_widget(lb)
            except Exception:
                pass
        self._lbls = []
        self.canvas.after.clear()
        pl, pr, pt, pb = dp(30), dp(10), dp(14), dp(24)
        x0 = self.x + pl
        y0 = self.y + pb
        w = max(self.width - pl - pr, 1)
        h = max(self.height - pt - pb, 1)

        def Y(v):
            return y0 + h * (v - self.ymin) / float(self.ymax - self.ymin)

        with self.canvas.after:
            Color(rgba=C(theme.DIVIDER))
            for gv in (60, 100, 140, 180):
                gy = Y(gv)
                Line(points=[x0, gy, x0 + w, gy], width=1)
            recs = self.records
            n = len(recs)
            if n:
                step = w / float(n)
                bw = min(dp(11), step * 0.52)
                for i, r in enumerate(recs):
                    cx = x0 + step * (i + 0.5)
                    s, d = int(r['systolic']), int(r['diastolic'])
                    col = theme.level_color(s, d)
                    y_hi, y_lo = Y(max(s, d)), Y(min(s, d))
                    Color(rgba=C(col))
                    Rectangle(pos=(cx - bw / 2.0, y_lo),
                              size=(bw, max(y_hi - y_lo, dp(2))))
        # 纵轴刻度
        for gv in (60, 100, 140, 180):
            lb = L(str(gv), 10, theme.TEXT_LIGHT)
            lb.pos = (self.x + dp(2), Y(gv) - dp(7))
            self.add_widget(lb)
            self._lbls.append(lb)
        # 横轴日期（抽样）
        n = len(self.records)
        if n:
            step = w / float(n)
            stride = max(1, n // 8)
            for i in range(0, n, stride):
                t = self.records[i]['measure_time']
                lb = L(t[5:10], 9, theme.TEXT_LIGHT)
                lb.pos = (x0 + step * (i + 0.5) - dp(15), self.y + dp(4))
                self.add_widget(lb)
                self._lbls.append(lb)


# ---------------- 趋势折线图 ----------------
class LineChart(FloatLayout):
    """series: [(字段key, 颜色key, 名称)]"""

    def __init__(self, series=None, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, None)
        self.height = dp(220)
        self.series = series or []
        self.rows = []
        self._lbls = []
        with self.canvas.before:
            Color(rgba=C(theme.CARD))
            self._bg = RoundedRectangle(pos=self.pos, size=self.size,
                                        radius=[dp(14)])
        self.bind(pos=self._on_geom, size=self._on_geom)

    def _on_geom(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self.redraw()

    def set_data(self, rows):
        self.rows = list(rows or [])
        self.redraw()

    def clear_labels(self):
        for lb in self._lbls:
            try:
                self.remove_widget(lb)
            except Exception:
                pass
        self._lbls = []

    def redraw(self, *a):
        self.clear_labels()
        self.canvas.after.clear()
        pl, pr, pt, pb = dp(30), dp(12), dp(26), dp(24)
        x0 = self.x + pl
        y0 = self.y + pb
        w = max(self.width - pl - pr, 1)
        h = max(self.height - pt - pb, 1)
        n = len(self.rows)
        if n < 1:
            return

        vals = []
        for r in self.rows:
            for key, _c, _name in self.series:
                v = r.get(key)
                if v is not None:
                    vals.append(v)
        if not vals:
            return
        vmin, vmax = min(vals), max(vals)
        span = max(vmax - vmin, 1)
        vmin -= span * 0.2
        vmax += span * 0.2
        span = vmax - vmin

        def X(i):
            return x0 + (w * i / float(n - 1) if n > 1 else w / 2.0)

        def Y(v):
            return y0 + h * (v - vmin) / span

        with self.canvas.after:
            Color(rgba=C(theme.DIVIDER))
            for i in range(4):
                gy = y0 + h * i / 3.0
                Line(points=[x0, gy, x0 + w, gy], width=1)
            for key, ckey, _name in self.series:
                col = getattr(theme, ckey, theme.PRIMARY)
                pts = []
                for i, r in enumerate(self.rows):
                    v = r.get(key)
                    if v is None:
                        continue
                    pts += [X(i), Y(v)]
                if len(pts) >= 4:
                    Color(rgba=C(col))
                    Line(points=pts, width=dp(2))
                    for i, r in enumerate(self.rows):
                        v = r.get(key)
                        if v is None:
                            continue
                        Color(rgba=C(col))
                        Ellipse(pos=(X(i) - dp(2.5), Y(v) - dp(2.5)),
                                size=(dp(5), dp(5)))
        # 纵轴刻度
        for i in range(4):
            gv = vmax - span * i / 3.0
            lb = L('%d' % round(gv), 9, theme.TEXT_LIGHT)
            lb.pos = (self.x + dp(2), y0 + h * i / 3.0 - dp(6))
            self.add_widget(lb)
            self._lbls.append(lb)
        # 横轴标签
        stride = max(1, n // 6)
        for i in range(0, n, stride):
            lb = L(str(self.rows[i].get('label', '')), 9, theme.TEXT_LIGHT)
            lb.pos = (X(i) - dp(14), self.y + dp(4))
            self.add_widget(lb)
            self._lbls.append(lb)
        # 图例
        lx = x0
        for key, ckey, name in self.series:
            lb = L('● ' + name, 11, getattr(theme, ckey, theme.PRIMARY))
            lb.pos = (lx, self.y + self.height - dp(20))
            self.add_widget(lb)
            self._lbls.append(lb)
            lx += dp(78)


# ---------------- 弹窗 ----------------
def confirm_dialog(title, message, on_ok, ok_text='确定', cancel_text='取消',
                  on_cancel=None):
    from kivy.uix.popup import Popup
    content = BoxLayout(orientation='vertical', padding=dp(18), spacing=dp(14))
    content.add_widget(L(message, 15, theme.TEXT))
    btns = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
    popup = Popup(title=title, content=content, size_hint=(0.86, None),
                  height=dp(230), auto_dismiss=False,
                  background='', background_color=C(theme.BG2),
                  separator_color=C(theme.PRIMARY))

    def ok(inst):
        popup.dismiss()
        if on_ok:
            on_ok()

    def cancel(inst):
        popup.dismiss()
        if on_cancel:
            on_cancel()

    btns.add_widget(B(cancel_text, bg=theme.CARD_LIGHT, color=theme.TEXT,
                      on_press=cancel))
    btns.add_widget(B(ok_text, bg=theme.PRIMARY, on_press=ok))
    content.add_widget(btns)
    popup.open()
    return popup


def message_dialog(title, message, ok_text='好的'):
    from kivy.uix.popup import Popup
    content = BoxLayout(orientation='vertical', padding=dp(18), spacing=dp(14))
    content.add_widget(L(message, 15, theme.TEXT))
    popup = Popup(title=title, content=content, size_hint=(0.86, None),
                  height=dp(210), auto_dismiss=True,
                  background='', background_color=C(theme.BG2),
                  separator_color=C(theme.PRIMARY))
    content.add_widget(B(ok_text, bg=theme.PRIMARY,
                         on_press=lambda inst: popup.dismiss()))
    popup.open()
    return popup
