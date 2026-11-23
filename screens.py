# -*- coding: utf-8 -*-
"""
应用页面（深色极简风）
记录 / 分析 / 知识 / 文章详情 / 我的 / 新增记录
"""

import os
import math
from datetime import datetime, timedelta

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.switch import Switch
from kivy.graphics import Color, RoundedRectangle, Rectangle, Ellipse, Line
from kivy.metrics import dp, sp
from kivy.clock import Clock

import theme
import icons
from appinfo import APP_NAME, APP_VERSION
import share
from theme import C
from widgets import (L, B, Card, TopBar, TI, BarChart, LineChart,
                     confirm_dialog, message_dialog, VoiceWave)
from voice_parser import parse_voice_text, validate
from voice import VoiceRecognizer


# ---------------- 工具 ----------------
def short_time(t):
    """'2026-11-23 10:30:00' -> '11-23 10:30'"""
    return t[5:16] if t else ''


def full_date(t):
    return t[:10] if t else ''


def ensure_mic(cb):
    """确保拿到麦克风权限后再回调（Android 需要运行时授权）。
    cb(granted: bool)"""
    try:
        from android.permissions import (request_permissions,
                                         check_permission, Permission)
        if check_permission(Permission.RECORD_AUDIO):
            Clock.schedule_once(lambda dt: cb(True), 0)
            return

        def on_done(perms, grants):
            ok = bool(grants) and bool(grants[0])
            Clock.schedule_once(lambda dt: cb(ok), 0)

        request_permissions([Permission.RECORD_AUDIO], on_done)
    except Exception:
        # 非 Android 平台或模块缺失：直接放行
        Clock.schedule_once(lambda dt: cb(True), 0)


# ================= 科普知识库 =================
ARTICLES = [
    {
        'title': '理解血压指数的含义',
        'emoji': '🩺', 'color': '#3B82F6', 'kind': 'scope',
        'summary': '高压、低压分别代表什么？',
        'body': [
            ('什么是收缩压（高压）',
             '心脏收缩把血液泵入动脉时，血管壁受到的最高压力就是收缩压，'
             '它反映心脏的泵血能力与血管弹性。'),
            ('什么是舒张压（低压）',
             '心脏舒张、瓣膜关闭时，血管壁仍保持的最低压力叫做舒张压，'
             '主要受外周血管阻力影响。'),
            ('正常参考范围',
             '一般成年人理想血压为收缩压低于 120 mmHg 且舒张压低于 80 mmHg。'
             '血压会随年龄、情绪、运动而波动，单次偏高不能直接诊断为高血压。'),
        ],
    },
    {
        'title': '高血压的类型和症状',
        'emoji': '❤️', 'color': '#E23A4B', 'kind': 'heart',
        'summary': '原发性 vs 继发性，有哪些信号？',
        'body': [
            ('原发性高血压',
             '约占全部高血压的 90% 以上，与遗传、高盐饮食、肥胖、'
             '吸烟饮酒、长期压力等因素相关，需要长期管理。'),
            ('继发性高血压',
             '由肾脏疾病、内分泌问题、睡眠呼吸暂停等明确病因引起，'
             '治疗原发病后血压可能恢复正常。'),
            ('常见信号',
             '头晕、头痛、颈项发紧、心悸、视物模糊等都可能是提示，'
             '但也有很多人没有任何症状，因此定期测量非常重要。'),
        ],
    },
    {
        'title': '深度解析血压波动性',
        'emoji': '🌊', 'color': '#12B5A5', 'kind': 'wave',
        'summary': '为什么每次测的数值都不一样？',
        'body': [
            ('昼夜节律',
             '血压天然存在昼夜变化：白天活动时偏高，夜间睡眠时下降，'
             '医学上称为「杓型」曲线，这是正常现象。'),
            ('影响因素',
             '情绪紧张、气温变化、睡眠质量、盐摄入量、饮酒、'
             '咖啡因和运动都会让读数上下浮动。'),
            ('正确做法',
             '倡导家庭自测、每天固定时间测量并记录，复诊时以连续多日'
             '的平均值作为判断依据，避免凭单次结果下结论。'),
        ],
    },
    {
        'title': '什么样的情况需要家庭血压测量？',
        'emoji': '🏠', 'color': '#F5C518', 'kind': 'house',
        'summary': '哪些人特别建议在家自测？',
        'body': [
            ('建议自测的人群',
             '已确诊高血压者、血压处于正常高值者、有高血压家族史者、'
             '孕产妇以及老年人群，都建议规律在家测量。'),
            ('白大褂高血压',
             '在医院测偏高、回家测正常，称为「白大褂高血压」，'
             '家庭测量能避免不必要的紧张和过度治疗。'),
            ('隐匿性高血压',
             '相反，在医院正常、在家偏高也值得警惕，'
             '家庭监测有助于早期发现这类情况。'),
        ],
    },
    {
        'title': '如何正确掌握家庭血压测量',
        'emoji': '📏', 'color': '#2ED573', 'kind': 'ruler',
        'summary': '测量姿势与流程的正确要点',
        'body': [
            ('测量前准备',
             '测前 30 分钟避免咖啡、运动和吸烟，提前排空膀胱，'
             '静坐休息至少 5 分钟后再开始。'),
            ('标准姿势',
             '袖带下缘距肘窝约 2~3 厘米，与心脏保持同一高度；'
             '坐姿端正、双脚平放、手臂自然放在桌面上。'),
            ('测量方法',
             '连续测量 2~3 次，每次间隔 1 分钟，取后两次的平均值记录；'
             '建议早晚各测一次，连续记录 7 天更准确。'),
        ],
    },
    {
        'title': '关于血压的一些常见误区与解答',
        'emoji': '💬', 'color': '#8B5CF6', 'kind': 'chat',
        'summary': '这些说法到底对不对？',
        'body': [
            ('「没有症状就不用治」——错误',
             '高血压常常毫无症状，却会持续损害心、脑、肾和眼底血管，'
             '等到出现症状往往已经造成不可逆的损伤。'),
            ('「血压正常就自己停药」——错误',
             '大多数高血压需要长期甚至终身管理，是否减药停药'
             '必须由医生根据监测记录判断。'),
            ('「一天测一次就够了」——不够',
             '早晚各测一次、连续记录数日，才能真实反映血压水平，'
             '单次数值容易受到偶然因素干扰。'),
        ],
    },
]

# ================= 记录页（首页）=================
class DashCard(Card):
    """最新数据看板：超大字号并排展示 高压 / 低压 / 脉搏"""

    def __init__(self, rec):
        super().__init__()
        self.padding = [dp(12), dp(10)]
        self.spacing = dp(6)
        if not rec:
            self.add_widget(L('暂无数据', 13, theme.TEXT_LIGHT))
            return
        key, txt = theme.bp_level(rec['systolic'], rec['diastolic'])
        col = getattr(theme, key)
        cells = [
            ('收缩压', rec['systolic'], 'mmHg', col),
            ('舒张压', rec['diastolic'], 'mmHg', col),
            ('脉搏', rec['pulse'], '次/分', theme.PRIMARY),
        ]
        row = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(74))
        for nm, val, unit, c in cells:
            cell = BoxLayout(orientation='vertical', size_hint_x=1, spacing=dp(1))
            cell.add_widget(L(nm, 11, theme.TEXT_LIGHT, align='center',
                              expand=True))
            cell.add_widget(L(str(val), 32, c, bold=True, align='center',
                              expand=True))
            cell.add_widget(L(unit, 10, theme.TEXT_LIGHT, align='center',
                              expand=True))
            row.add_widget(cell)
        self.add_widget(row)
        # 与「最近测量」拉开距离（中间加分隔线）
        div = Widget(size_hint_y=None, height=dp(1))
        with div.canvas.before:
            Color(rgba=C(theme.DIVIDER))
            rect = Rectangle(pos=div.pos, size=div.size)
        div.bind(pos=lambda inst, v: setattr(rect, 'pos', inst.pos),
                 size=lambda inst, v: setattr(rect, 'size', inst.size))
        self.add_widget(div)
        foot = BoxLayout(size_hint_y=None, height=dp(26), spacing=dp(8))
        foot.add_widget(L('● ' + txt, 13, col, bold=True))
        foot.add_widget(L('最近测量  ' + short_time(rec['measure_time']),
                           11, theme.TEXT_LIGHT))
        if rec.get('note'):
            foot.add_widget(L(rec['note'], 11, theme.TEXT_LIGHT, shorten=True))
        self.add_widget(foot)


class RecordItem(BoxLayout):
    """历史记录卡片：血压值居中靠右 + 左状态色条 + 编辑/删除"""

    def __init__(self, rec, on_edit, on_delete, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(98)
        self.padding = [0, dp(8)]
        self.spacing = dp(6)
        key, txt = theme.bp_level(rec['systolic'], rec['diastolic'])
        col = getattr(theme, key)
        with self.canvas.before:
            Color(rgba=C(theme.CARD))
            self._bg = RoundedRectangle(pos=self.pos, size=self.size,
                                        radius=[dp(14)])
            Color(rgba=C(col))
            self._bar = Rectangle(pos=(self.x, self.y),
                                  size=(dp(5), self.height))
        self.bind(pos=self._upd, size=self._upd)

        # 左侧：时间 + 脉搏/备注
        mid = BoxLayout(orientation='vertical', spacing=dp(4), size_hint_x=1,
                        padding=[dp(10), dp(6)])
        mid.add_widget(L(short_time(rec['measure_time']), 12,
                         theme.TEXT_LIGHT))
        line = '脉搏 %d 次/分' % rec['pulse']
        if rec.get('note'):
            line += '   ·   ' + rec['note']
        mid.add_widget(L(line, 11, theme.TEXT_LIGHT, shorten=True))
        self.add_widget(mid)

        # 右侧：血压值（居中靠右）+ 状态 + 编辑/删除
        right = BoxLayout(orientation='vertical', size_hint_x=None,
                          width=dp(112), spacing=dp(1), padding=[0, dp(5)])
        right.add_widget(L('%d/%d' % (rec['systolic'], rec['diastolic']),
                           22, col, bold=True, align='center', expand=True))
        right.add_widget(L(txt, 11, col, align='center'))
        ops = BoxLayout(size_hint_y=None, height=dp(32), spacing=dp(6))
        ops.add_widget(B(icons.ic('edit'), bg=theme.CARD_LIGHT,
                          color=theme.TEXT, size=15, height=32, radius=8,
                          font_name=icons.FONT_NAME, size_hint_x=1,
                          on_press=lambda inst: on_edit(rec)))
        ops.add_widget(B(icons.ic('delete'), bg=theme.CARD_LIGHT,
                          color=theme.DANGER, size=15, height=32, radius=8,
                          font_name=icons.FONT_NAME, size_hint_x=1,
                          on_press=lambda inst: on_delete(rec)))
        right.add_widget(ops)
        self.add_widget(right)

    def _upd(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._bar.pos = (self.x, self.y)
        self._bar.size = (dp(5), self.height)


class ChartCard(Card):
    """血压趋势柱状图（柱体由低压延伸到高压），左右滑动切换日/周/月"""

    def __init__(self, home, recs):
        super().__init__()
        self.home = home
        self.recs = list(recs or [])
        self.days = 7
        self._sx = None
        self._sy = 0
        head = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        head.add_widget(L('血压趋势', 16, theme.TEXT, bold=True))
        seg = BoxLayout(spacing=dp(6), size_hint_x=None, width=dp(160))
        self.btns = {}
        for d, label in ((1, '日'), (7, '周'), (30, '月')):
            b = B(label, bg=theme.CARD_LIGHT, color=theme.TEXT_LIGHT,
                  size=12, height=32, radius=8,
                  on_press=lambda inst, x=d: self.set_range(x))
            seg.add_widget(b)
            self.btns[d] = b
        head.add_widget(seg)
        self.add_widget(head)

        self.tag = L('', 12, theme.TEXT_LIGHT)
        self.add_widget(self.tag)

        self.bar = BarChart(size_hint=(1, None), height=dp(184))
        self.add_widget(self.bar)
        self.bar.bind(on_touch_down=self._td, on_touch_up=self._tu)

        self.msg = L('', 12, theme.TEXT_LIGHT)
        self.add_widget(self.msg)
        self.set_range(1)

    # ---------------- 滑动切换 ----------------
    def _td(self, inst, t):
        self._sx, self._sy = t.x, t.y
        return False

    def _tu(self, inst, t):
        if self._sx is None:
            return False
        dx, dy = t.x - self._sx, t.y - self._sy
        self._sx = None
        if abs(dx) > dp(42) and abs(dx) > abs(dy) * 1.4:
            order = [1, 7, 30]
            i = order.index(self.days)
            # 左滑 → 更大范围，右滑 → 更小范围
            i = i + 1 if dx < 0 else i - 1
            self.set_range(order[i % len(order)])
            return True
        return False

    def _rows(self, days):
        today = datetime.now().strftime('%Y-%m-%d')
        if days == 1:
            rows = [r for r in self.recs if r['measure_time'].startswith(today)]
        else:
            start = (datetime.now() - timedelta(days=days - 1)).strftime('%Y-%m-%d')
            rows = [r for r in self.recs if r['measure_time'][:10] >= start]
        return sorted(rows, key=lambda r: r['measure_time'])

    def set_range(self, days):
        self.days = days
        for d, b in self.btns.items():
            active = (d == days)
            b._ci.rgba = C(theme.PRIMARY if active else theme.CARD_LIGHT)
            b.color = C('#FFFFFF' if active else theme.TEXT_LIGHT)
            b.bold = active
        rows = self._rows(days)
        self.bar.set_data(rows)
        Clock.schedule_once(lambda dt: self.bar.redraw(), 0)
        if rows:
            s = sum(r['systolic'] for r in rows) / float(len(rows))
            d = sum(r['diastolic'] for r in rows) / float(len(rows))
            _k, txt = theme.bp_level(s, d)
            self.tag.text = ('平均 %d/%d mmHg · %s（左右滑动切换日/周/月）'
                             % (round(s), round(d), txt))
            self.tag.color = C(theme.level_color(s, d))
            self.msg.text = ''
        else:
            self.tag.text = ''
            self.msg.text = '该时间段暂无记录，先添加一条吧。'


class HomeScreen(Screen):
    def __init__(self, app, name='home', **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.app = app
        root = BoxLayout(orientation='vertical')
        root.add_widget(TopBar('我的血压', subtitle='本地存储 · 隐私安全'))
        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.content = BoxLayout(orientation='vertical', size_hint_y=None,
                                 spacing=dp(12),
                                 padding=[dp(14), dp(10)])
        self.content.bind(minimum_height=lambda i, v: setattr(i, 'height', v))
        self.scroll.add_widget(self.content)
        root.add_widget(self.scroll)
        bottom = BoxLayout(orientation='vertical', size_hint_y=None,
                           height=dp(96), padding=[dp(14), dp(8)])
        self.hint = L('轻点填写 · 长按直接说话', 11, theme.TEXT_LIGHT,
                      size_hint=(1, None), height=dp(16))
        bottom.add_widget(self.hint)
        # 声波动画（仅在语音识别时显示）
        self.wave_wrap = FloatLayout(size_hint_y=None, height=dp(0))
        self.wave = VoiceWave(size=(dp(170), dp(30)))
        self.wave.opacity = 0
        self.wave_wrap.add_widget(self.wave)
        self.wave_wrap.bind(pos=self._center_wave, size=self._center_wave)
        bottom.add_widget(self.wave_wrap)
        self.vr = None
        self.add_btn = B('＋  添加记录', bg=theme.PRIMARY, height=52,
                         size=16, bold=True, radius=14,
                         on_press=lambda i: self.app.goto('add'),
                         on_long_press=lambda *a: self.start_voice())
        bottom.add_widget(self.add_btn)
        root.add_widget(bottom)
        self.add_widget(root)
        self.bind(on_pre_enter=self._enter)

    def _center_wave(self, *a):
        self.wave.center = self.wave_wrap.center

    def _enter(self, *a):
        def ui(dt):
            self.refresh()
            # 回到记录页时从顶部开始，避免看板被隐藏在滚动下方
            self.scroll.scroll_y = 1.0
        Clock.schedule_once(ui, 0)

    def refresh(self):
        self.content.clear_widgets()
        recs = self.app.db.get_all()
        self.content.add_widget(DashCard(recs[0] if recs else None))
        self.content.add_widget(ChartCard(self, recs))
        head = BoxLayout(size_hint_y=None, height=dp(34))
        head.add_widget(L('历史记录', 16, theme.TEXT, bold=True))
        head.add_widget(L('共 %d 条' % len(recs), 12, theme.TEXT_LIGHT))
        self.content.add_widget(head)
        if not recs:
            c = Card()
            c.add_widget(L('还没有记录', 15, theme.TEXT, bold=True))
            c.add_widget(L('点击下方「添加记录」开始记录你的血压吧。',
                           12, theme.TEXT_LIGHT))
            self.content.add_widget(c)
            return
        for r in recs:
            self.content.add_widget(
                RecordItem(r, self.on_edit, self.on_delete))

    # ---------------- 操作 ----------------
    HINT_DEFAULT = '轻点填写 · 长按直接说话'

    def voice_running(self, on):
        """切换声波动画与按钮状态"""
        self.wave_wrap.height = dp(34) if on else dp(0)
        self.wave.opacity = 1 if on else 0
        if on:
            self.wave.center = self.wave_wrap.center
            self.wave.start()
        else:
            self.wave.stop()

    def start_voice(self):
        """长按「添加记录」：在当前页面直接语音录入，不跳转"""
        if self.vr is not None:
            return
        ensure_mic(self._do_start_voice)

    def _do_start_voice(self, granted=True):
        if not granted:
            self.hint.text = '未获得麦克风权限，请在系统设置中允许后重试。'
            Clock.schedule_once(lambda dt: self._restore_hint(), 3)
            return
        if not VoiceRecognizer().is_available():
            message_dialog('无法语音识别',
                           '当前设备不支持语音识别，请使用键盘输入。')
            return
        self.voice_running(True)
        self.hint.text = '正在聆听，请说出血压和脉搏…'
        self.vr = VoiceRecognizer(
            on_result=self._quick_result,
            on_partial=self._quick_partial,
            on_error=self._quick_err,
            on_ready=lambda: self._quick_status('正在输入… 请继续说'))
        self.vr.start()

    def _quick_partial(self, text):
        def ui(dt):
            if text:
                self.hint.text = '正在输入：%s' % text
        Clock.schedule_once(ui, 0)

    def _quick_status(self, txt):
        def ui(dt):
            self.hint.text = txt
        Clock.schedule_once(ui, 0)

    def _quick_result(self, text):
        def ui(dt):
            self.vr = None
            self.voice_running(False)
            parsed = parse_voice_text(text)
            s, d, p = (parsed['systolic'], parsed['diastolic'],
                       parsed['pulse'])
            if s is None or d is None or p is None:
                self.hint.text = '未识别到完整数据，请说出高压、低压和脉搏。'
                Clock.schedule_once(lambda dt: self._restore_hint(), 2.5)
                return
            msg = ('识别结果：\n\n'
                   '高压 %s mmHg\n低压 %s mmHg\n脉搏 %s 次/分\n\n确认保存吗？'
                   % (s, d, p))
            confirm_dialog('确认语音结果', msg,
                           lambda: self._quick_save(s, d, p),
                           ok_text='保存', cancel_text='重说一遍',
                           on_cancel=lambda: self.start_voice())
        Clock.schedule_once(ui, 0)

    def _quick_err(self, msg):
        def ui(dt):
            self.vr = None
            self.voice_running(False)
            self.hint.text = msg
            Clock.schedule_once(lambda dt: self._restore_hint(), 2.5)
        Clock.schedule_once(ui, 0)

    def _quick_save(self, s, d, p):
        warns = validate(s, d, p)
        if warns:
            confirm_dialog('数据提醒', '\n'.join(warns),
                           lambda: self._do_quick_save(s, d, p),
                           ok_text='仍然保存', cancel_text='取消')
            return
        self._do_quick_save(s, d, p)

    def _do_quick_save(self, s, d, p):
        self.app.db.add_record(
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'), s, d, p, '')
        self.hint.text = '已保存 %d/%d mmHg' % (s, d)
        Clock.schedule_once(lambda dt: self._restore_hint(), 2.5)
        self.refresh()

    def _restore_hint(self):
        self.hint.text = self.HINT_DEFAULT

    def on_edit(self, rec):
        self.app.editing_id = rec['id']
        self.app.goto('add')

    def on_delete(self, rec):
        confirm_dialog(
            '删除记录',
            '确定删除这条 %s 的记录吗？\n此操作不可恢复。' % short_time(rec['measure_time']),
            lambda: self._do_delete(rec['id']))

    def _do_delete(self, rid):
        self.app.db.delete_record(rid)
        self.refresh()


# ================= 新增 / 编辑记录 =================
class AddScreen(Screen):
    def __init__(self, app, name='add', **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.app = app
        root = BoxLayout(orientation='vertical')
        self.topbar = TopBar('记录血压', show_back=True,
                             on_back=lambda: self.app.goto('home'))
        root.add_widget(self.topbar)
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        body = BoxLayout(orientation='vertical', size_hint_y=None,
                          spacing=dp(12), padding=[dp(14), dp(10)])
        body.bind(minimum_height=lambda i, v: setattr(i, 'height', v))
        scroll.add_widget(body)
        root.add_widget(scroll)

        c = Card()
        c.add_widget(L('测量时间', 13, theme.TEXT_LIGHT))
        row = BoxLayout(spacing=dp(10))
        self.d_in = TI(text='', height=44)
        self.t_in = TI(text='', height=44)
        row.add_widget(self.d_in)
        row.add_widget(self.t_in)
        c.add_widget(row)
        body.add_widget(c)

        c2 = Card()
        c2.add_widget(L('血压数值（mmHg）', 13, theme.TEXT_LIGHT))
        r = BoxLayout(spacing=dp(10))
        self.sys = TI(hint='收缩压（高压）', height=44)
        self.dia = TI(hint='舒张压（低压）', height=44)
        r.add_widget(self.sys)
        r.add_widget(self.dia)
        c2.add_widget(r)
        self.pul = TI(hint='脉搏（次/分）', height=44)
        c2.add_widget(self.pul)
        self.note = TI(hint='备注（选填）', input_type='text', height=44)
        c2.add_widget(self.note)
        for ti in (self.sys, self.dia, self.pul):
            ti.bind(on_text=lambda inst: self.highlight())
        body.add_widget(c2)

        vb = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        self.mic = B(icons.im('mic') + '  语音输入', bg=theme.CARD_LIGHT,
                     color=theme.TEXT, height=48, radius=12, size=14, bold=True,
                     markup=True,
                     on_press=lambda i: self.toggle_voice())
        vb.add_widget(self.mic)
        body.add_widget(vb)
        self.status = L('说：「高压一百二，低压八十，脉搏七十二」',
                        12, theme.TEXT_LIGHT)
        body.add_widget(self.status)
        self.wave_wrap = FloatLayout(size_hint_y=None, height=dp(0))
        self.wave = VoiceWave(size=(dp(170), dp(28)))
        self.wave.opacity = 0
        self.wave_wrap.add_widget(self.wave)
        self.wave_wrap.bind(pos=self._center_wave, size=self._center_wave)
        body.add_widget(self.wave_wrap)

        sv = BoxLayout(size_hint_y=None, height=dp(56), padding=[0, dp(4)])
        sv.add_widget(B('保存记录', bg=theme.PRIMARY, height=52, size=16,
                       bold=True, radius=14,
                       on_press=lambda i: self.save()))
        body.add_widget(sv)
        self.add_widget(root)
        self.vr = None
        self.bind(on_pre_enter=lambda *a: self._enter())

    def _enter(self):
        rid = getattr(self.app, 'editing_id', None)
        if rid:
            rec = self.app.db.get_by_id(rid)
            if rec:
                self.topbar.title_lbl.text = '编辑记录'
                self.fill(rec)
            return
        self.topbar.title_lbl.text = '记录血压'
        self.clear_form()
        self.d_in.text = datetime.now().strftime('%Y-%m-%d')
        self.t_in.text = datetime.now().strftime('%H:%M')

    def fill(self, rec):
        self.d_in.text = full_date(rec['measure_time'])
        self.t_in.text = rec['measure_time'][11:16]
        self.sys.text = str(rec['systolic'])
        self.dia.text = str(rec['diastolic'])
        self.pul.text = str(rec['pulse'])
        self.note.text = rec.get('note') or ''
        self.status.text = '正在编辑已有记录，修改后保存即可。'
        self._clear_hl()

    def clear_form(self):
        self.sys.text = ''
        self.dia.text = ''
        self.pul.text = ''
        self.note.text = ''
        self.status.text = '说：「高压一百二，低压八十，脉搏七十二」'
        self.mic.text = icons.im('mic') + '  语音输入'
        self._clear_hl()

    # ---------------- 异常高亮 ----------------
    def _num(self, ti):
        try:
            return int(ti.text.strip())
        except Exception:
            return None

    def _clear_hl(self):
        for ti in (self.sys, self.dia, self.pul):
            ti.set_border(None)

    def highlight(self):
        """超出正常范围→黄色描边；高压≤低压→红色描边（仍允许保存）"""
        s, d, p = self._num(self.sys), self._num(self.dia), self._num(self.pul)
        self._clear_hl()
        if s is not None and (s < 70 or s > 250):
            self.sys.set_border(theme.WARNING)
        if d is not None and (d < 40 or d > 150):
            self.dia.set_border(theme.WARNING)
        if p is not None and (p < 30 or p > 200):
            self.pul.set_border(theme.WARNING)
        if s is not None and d is not None and s <= d:
            self.sys.set_border(theme.DANGER)
            self.dia.set_border(theme.DANGER)

    # ---------------- 语音 ----------------
    def _center_wave(self, *a):
        self.wave.center = self.wave_wrap.center

    def _set_listening(self, on):
        self.wave_wrap.height = dp(32) if on else dp(0)
        self.wave.opacity = 1 if on else 0
        if on:
            self.wave.center = self.wave_wrap.center
            self.wave.start()
            self.mic.text = icons.im('close') + '  停止聆听'
        else:
            self.wave.stop()
            self.mic.text = icons.im('mic') + '  语音输入'

    def toggle_voice(self):
        if self.vr is not None:
            self.vr.stop()
            self.vr = None
            self._set_listening(False)
            self.status.text = '已停止聆听，可点击「语音输入」重新识别。'
            return
        self.start_voice()

    def start_voice(self):
        if self.vr is not None:
            return
        ensure_mic(self._do_start)

    def _do_start(self, granted=True):
        if not granted:
            self.status.text = '未获得麦克风权限，请在系统设置中允许后重试。'
            return
        if not VoiceRecognizer().is_available():
            message_dialog('无法语音识别',
                           '当前设备不支持语音识别，请使用键盘输入。')
            return
        self._set_listening(True)
        self.status.text = '正在聆听，请说出血压和脉搏…'
        self.vr = VoiceRecognizer(
            on_result=self.on_voice,
            on_partial=self._on_partial,
            on_error=self.on_voice_err,
            on_ready=lambda: self.set_status('正在输入… 请继续说'))
        self.vr.start()

    def _on_partial(self, text):
        def ui(dt):
            if text:
                self.status.text = '正在输入：%s' % text
        Clock.schedule_once(ui, 0)

    def set_status(self, txt):
        def ui(dt):
            self.status.text = txt
        Clock.schedule_once(ui, 0)

    def on_voice(self, text):
        def ui(dt):
            self.vr = None
            self._set_listening(False)
            parsed = parse_voice_text(text)
            s, d, p = (parsed['systolic'], parsed['diastolic'],
                       parsed['pulse'])
            if s is None and d is None and p is None:
                self.status.text = '没有识别到有效内容，请再试一次。'
                return
            msg = ('识别结果：\n\n'
                   '高压 %s mmHg\n低压 %s mmHg\n脉搏 %s 次/分\n\n确认填入吗？'
                   % ('—' if s is None else s,
                      '—' if d is None else d,
                      '—' if p is None else p))
            confirm_dialog('确认语音结果', msg, lambda: self._apply_voice(s, d, p),
                           ok_text='填入', cancel_text='重说一遍')
        Clock.schedule_once(ui, 0)

    def on_voice_err(self, msg):
        def ui(dt):
            self.vr = None
            self._set_listening(False)
            self.status.text = msg
        Clock.schedule_once(ui, 0)

    def _apply_voice(self, s, d, p):
        if s is not None:
            self.sys.text = str(s)
        if d is not None:
            self.dia.text = str(d)
        if p is not None:
            self.pul.text = str(p)
        self.status.text = '已填入，请核对后点击「保存记录」。'
        self.highlight()

    # ---------------- 保存 ----------------
    def save(self):
        date_s = self.d_in.text.strip()
        time_s = self.t_in.text.strip()
        try:
            datetime.strptime(date_s + ' ' + time_s, '%Y-%m-%d %H:%M')
            measure = date_s + ' ' + time_s + ':00'
        except Exception:
            message_dialog('时间格式不正确',
                           '请按 YYYY-MM-DD 与 HH:MM 填写测量时间。')
            return
        s, d, p = (self.sys.text.strip(), self.dia.text.strip(),
                   self.pul.text.strip())
        if not s or not d or not p:
            message_dialog('数据不完整', '请填写高压、低压和脉搏。')
            return
        try:
            si, di, pi = int(s), int(d), int(p)
        except ValueError:
            message_dialog('格式错误', '请输入有效的数字。')
            return
        warns = validate(si, di, pi)

        def do_save():
            note = self.note.text.strip()
            rid = getattr(self.app, 'editing_id', None)
            if rid:
                self.app.db.update_record(rid, measure, si, di, pi, note)
                self.app.editing_id = None
            else:
                self.app.db.add_record(measure, si, di, pi, note)
            self.clear_form()
            self.app.goto('home')

        if warns:
            confirm_dialog('数据提示', '\n'.join(warns) + '\n\n仍要保存吗？',
                           do_save, ok_text='仍然保存')
        else:
            do_save()


# ================= 分析页 =================
class HBar(Widget):
    """水平占比条"""

    def __init__(self, ratio=0.0, color=None, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(10)
        self.ratio = max(0.0, min(1.0, ratio))
        self.color = color or theme.PRIMARY
        with self.canvas.before:
            Color(rgba=C(theme.CARD_LIGHT))
            self._bg = RoundedRectangle(pos=self.pos, size=self.size,
                                        radius=[dp(5)])
        with self.canvas.after:
            Color(rgba=C(self.color))
            self._fg = RoundedRectangle(pos=self.pos, size=self.size,
                                        radius=[dp(5)])
        self.bind(pos=self._u, size=self._u)

    def _u(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._fg.pos = self.pos
        self._fg.size = (self.width * self.ratio, self.height)


class AnalysisScreen(Screen):
    LEVELS = [('正常', 'SUCCESS'), ('正常高值', 'WARNING'),
              ('偏高', 'ORANGE'), ('高血压', 'DANGER'), ('偏低', 'LOW')]

    def __init__(self, app, name='analysis', **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.app = app
        self.mode = '7'
        root = BoxLayout(orientation='vertical')
        root.add_widget(TopBar('数据分析'))
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        body = BoxLayout(orientation='vertical', size_hint_y=None,
                          spacing=dp(12), padding=[dp(14), dp(10)])
        body.bind(minimum_height=lambda i, v: setattr(i, 'height', v))
        scroll.add_widget(body)
        root.add_widget(scroll)
        self.scroll = scroll
        self.body = body

        seg = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        self.btns = {}
        for m, label in (('7', '近 7 天'), ('30', '近 30 天'),
                          ('custom', '自定义'), ('all', '全部')):
            b = B(label, bg=theme.CARD_LIGHT, color=theme.TEXT_LIGHT,
                  size=13, height=38, radius=10,
                  on_press=lambda inst, x=m: self.set_mode(x))
            seg.add_widget(b)
            self.btns[m] = b
        body.add_widget(seg)

        # 自定义时间范围
        self.custom_card = Card()
        self.custom_card.add_widget(
            L('自定义范围', 13, theme.TEXT_LIGHT))
        r = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.c_start = TI(hint='开始 2026-11-01', height=44)
        self.c_end = TI(hint='结束 2026-11-23', height=44)
        r.add_widget(self.c_start)
        r.add_widget(self.c_end)
        self.custom_card.add_widget(r)
        self.custom_card.add_widget(
            B('应用范围', bg=theme.PRIMARY, height=40, size=13, radius=10,
              on_press=lambda i: self.apply_custom()))
        body.add_widget(self.custom_card)

        self.avg_card = Card()
        body.add_widget(self.avg_card)

        self.chart_card = Card()
        self.chart_card.add_widget(L('变化趋势', 15, theme.TEXT, bold=True))
        self.chart = LineChart(series=[
            ('systolic', 'PRIMARY', '收缩压'),
            ('diastolic', 'SUCCESS', '舒张压'),
            ('pulse', 'LOW', '脉搏'),
        ])
        self.chart_card.add_widget(self.chart)
        self.chart_msg = L('', 12, theme.TEXT_LIGHT)
        self.chart_card.add_widget(self.chart_msg)
        body.add_widget(self.chart_card)

        self.dist_card = Card()
        self.dist_card.add_widget(L('健康状态分布', 15, theme.TEXT, bold=True))
        body.add_widget(self.dist_card)
        self.add_widget(root)
        self.bind(on_pre_enter=lambda *a:
                  Clock.schedule_once(lambda dt: (
                      self.refresh(),
                      setattr(self.scroll, 'scroll_y', 1.0)), 0))

    # ---------------- 数据 ----------------
    def _records(self):
        recs = self.app.db.get_all()
        if self.mode == 'all':
            return recs
        if self.mode == 'custom':
            return self._custom_records(recs)
        days = int(self.mode)
        start = (datetime.now() - timedelta(days=days - 1)).strftime('%Y-%m-%d')
        return [r for r in recs if r['measure_time'][:10] >= start]

    def _custom_records(self, recs):
        s = self.c_start.text.strip()[:10]
        e = self.c_end.text.strip()[:10]
        try:
            ds = datetime.strptime(s, '%Y-%m-%d')
            de = datetime.strptime(e, '%Y-%m-%d')
        except Exception:
            return []
        end = (de + timedelta(days=1)).strftime('%Y-%m-%d')
        return [r for r in recs if ds.strftime('%Y-%m-%d')
                <= r['measure_time'][:10] < end]

    def apply_custom(self):
        s = self.c_start.text.strip()[:10]
        e = self.c_end.text.strip()[:10]
        try:
            datetime.strptime(s, '%Y-%m-%d')
            datetime.strptime(e, '%Y-%m-%d')
        except Exception:
            message_dialog('日期格式不正确',
                           '请按 YYYY-MM-DD 填写开始与结束日期。')
            return
        if s > e:
            message_dialog('日期不正确', '开始日期不能晚于结束日期。')
            return
        self.set_mode('custom')

    @staticmethod
    def _daily(recs):
        groups, order = {}, []
        for r in sorted(recs, key=lambda x: x['measure_time']):
            d = r['measure_time'][:10]
            if d not in groups:
                groups[d] = []
                order.append(d)
            groups[d].append(r)
        out = []
        for d in order:
            g = groups[d]
            n = float(len(g))
            out.append({
                'label': d[5:],
                'systolic': round(sum(x['systolic'] for x in g) / n, 1),
                'diastolic': round(sum(x['diastolic'] for x in g) / n, 1),
                'pulse': round(sum(x['pulse'] for x in g) / n, 1),
            })
        return out

    def set_mode(self, m):
        self.mode = m
        for k, b in self.btns.items():
            active = (k == m)
            b._ci.rgba = C(theme.PRIMARY if active else theme.CARD_LIGHT)
            b.color = C('#FFFFFF' if active else theme.TEXT_LIGHT)
            b.bold = active
        self.refresh()

    def refresh(self):
        recs = self._records()

        # 平均值
        self.avg_card.clear_widgets()
        if not recs:
            self.avg_card.add_widget(L('所选范围内暂无数据', 13, theme.TEXT_LIGHT))
        else:
            n = float(len(recs))
            cells = [
                ('平均高压', round(sum(r['systolic'] for r in recs) / n, 1), 'mmHg'),
                ('平均低压', round(sum(r['diastolic'] for r in recs) / n, 1), 'mmHg'),
                ('平均脉搏', round(sum(r['pulse'] for r in recs) / n, 1), 'BPM'),
            ]
            row = BoxLayout(spacing=dp(6))
            for nm, val, unit in cells:
                cell = BoxLayout(orientation='vertical', spacing=dp(1))
                cell.add_widget(L(nm, 11, theme.TEXT_LIGHT))
                cell.add_widget(L(str(val), 26, theme.TEXT, bold=True))
                cell.add_widget(L(unit, 10, theme.TEXT_LIGHT))
                row.add_widget(cell)
            self.avg_card.add_widget(row)
            self.avg_card.add_widget(
                L('共 %d 条记录' % len(recs), 11, theme.TEXT_LIGHT))

        # 趋势
        daily = self._daily(recs)
        self.chart.set_data(daily)
        Clock.schedule_once(lambda dt: self.chart.redraw(), 0)
        self.chart_msg.text = ('' if daily
                              else '该范围内没有记录，无法绘制趋势。')

        # 状态分布
        self.dist_card.clear_widgets()
        self.dist_card.add_widget(L('健康状态分布', 15, theme.TEXT, bold=True))
        if not recs:
            self.dist_card.add_widget(L('暂无数据', 12, theme.TEXT_LIGHT))
            return
        counts = {name: 0 for name, _k in self.LEVELS}
        for r in recs:
            _key, txt = theme.bp_level(r['systolic'], r['diastolic'])
            if txt in counts:
                counts[txt] += 1
        total = float(len(recs))
        for name, ckey in self.LEVELS:
            cnt = counts.get(name, 0)
            row = BoxLayout(size_hint_y=None, height=dp(24), spacing=dp(10))
            row.add_widget(L(name, 12, theme.TEXT_LIGHT, width=dp(64)))
            row.add_widget(HBar(ratio=cnt / total,
                                color=getattr(theme, ckey)))
            row.add_widget(L('%d 条 · %.0f%%' % (cnt, cnt / total * 100),
                             11, theme.TEXT_LIGHT, width=dp(96),
                             align='right'))
            self.dist_card.add_widget(row)


# ================= 知识页 =================
class ArtIcon(Widget):
    """科普卡片右侧的白色矢量插画"""

    def __init__(self, kind='heart', **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(56), dp(56))
        self.kind = kind
        with self.canvas.before:
            Color(rgba=(1, 1, 1, 0.16))
            self._plate = Ellipse(pos=self.pos, size=self.size)
        self.bind(pos=self._u, size=self._u)

    def _u(self, *a):
        self._plate.pos = self.pos
        self._plate.size = self.size
        self._draw()

    def _draw(self):
        c = self.canvas.after
        c.clear()
        cx, cy = self.center_x, self.center_y
        k = self.kind
        with c:
            Color(rgba=(1, 1, 1, 0.95))
            if k == 'heart':
                pts = []
                for i in range(29):
                    t = i / 28.0 * 6.2832
                    x = 16 * (math.sin(t) ** 3)
                    y = (13 * math.cos(t) - 5 * math.cos(2 * t)
                         - 2 * math.cos(3 * t) - math.cos(4 * t))
                    pts += [cx + dp(1.5) * x, cy - dp(1.5) * y]
                Line(points=pts, close=True, width=dp(2), joint='round')
            elif k == 'wave':
                pts = []
                for i in range(25):
                    x = i / 24.0
                    pts += [cx - dp(20) + dp(40) * x,
                            cy + dp(9) * math.sin(x * 6.2832)]
                Line(points=pts, width=dp(2.2))
            elif k == 'ruler':
                Line(rectangle=(cx - dp(18), cy - dp(9), dp(36), dp(18)),
                     width=dp(1.8))
                for i in range(5):
                    x = cx - dp(18) + dp(7.2) * i
                    ln = dp(5) if i % 2 == 0 else dp(3)
                    Line(points=[x, cy - dp(9), x, cy - dp(9) + ln],
                         width=dp(1.2))
            elif k == 'house':
                Line(rectangle=(cx - dp(13), cy - dp(2), dp(26), dp(16)),
                     width=dp(1.8))
                Line(points=[cx - dp(17), cy - dp(2), cx, cy - dp(17),
                             cx + dp(17), cy - dp(2)],
                     width=dp(1.8), joint='round')
            elif k == 'chat':
                Line(rounded_rectangle=(cx - dp(17), cy - dp(9), dp(34), dp(20),
                                        dp(6)), width=dp(1.8))
                Line(points=[cx - dp(8), cy - dp(9), cx - dp(12), cy - dp(18),
                             cx - dp(2), cy - dp(9)], width=dp(1.8),
                     joint='round')
                for i in range(3):
                    Ellipse(pos=(cx - dp(9) + dp(7) * i, cy - dp(2)),
                            size=(dp(3.6), dp(3.6)))
            else:  # scope 听诊器
                Line(circle=(cx - dp(2), cy + dp(3), dp(10)), width=dp(2))
                Line(points=[cx + dp(7), cy - dp(1), cx + dp(13), cy - dp(9),
                             cx + dp(19), cy - dp(4)], width=dp(2),
                     joint='round')
                Ellipse(pos=(cx + dp(16), cy - dp(9)), size=(dp(8), dp(8)))


class ArticleCard(BoxLayout):
    """彩色大圆角科普卡片：左侧标题 + 右侧矢量插画"""

    def __init__(self, art, on_open, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(96)
        self.padding = [dp(14), dp(10)]
        self.spacing = dp(12)
        with self.canvas.before:
            Color(rgba=C(art['color']))
            self._bg = RoundedRectangle(pos=self.pos, size=self.size,
                                        radius=[dp(18)])
        self.bind(pos=self._u, size=self._u)
        left = BoxLayout(orientation='vertical', spacing=dp(5), size_hint_x=1,
                         padding=[0, dp(8)])
        left.add_widget(L(art['title'], 16, '#FFFFFF', bold=True))
        left.add_widget(L(art['summary'], 11, (1, 1, 1, 0.88)))
        self.add_widget(left)
        wrap = BoxLayout(size_hint_x=None, width=dp(56),
                         padding=[0, dp(19)])
        wrap.add_widget(ArtIcon(art.get('kind', 'heart')))
        self.add_widget(wrap)
        self.bind(on_touch_down=self._tap)
        self._on_open = on_open

    def _u(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def _tap(self, inst, touch):
        if self.collide_point(*touch.pos):
            self._on_open()
            return True
        return False


class KnowledgeScreen(Screen):
    def __init__(self, app, name='knowledge', **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.app = app
        root = BoxLayout(orientation='vertical')
        root.add_widget(TopBar('血压科普', subtitle='专注血压健康知识'))
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        body = BoxLayout(orientation='vertical', size_hint_y=None,
                          spacing=dp(12), padding=[dp(14), dp(10)])
        body.bind(minimum_height=lambda i, v: setattr(i, 'height', v))
        scroll.add_widget(body)
        self.body = body
        root.add_widget(scroll)
        self.add_widget(root)
        self.bind(on_pre_enter=lambda *a: Clock.schedule_once(
            lambda dt: self.refresh(), 0))

    def refresh(self):
        self.body.clear_widgets()
        self.body.add_widget(
            L('共 %d 篇科普文章' % len(ARTICLES), 12, theme.TEXT_LIGHT))
        for i, art in enumerate(ARTICLES):
            self.body.add_widget(
                ArticleCard(art, on_open=lambda idx=i: self.open_article(idx)))

    def open_article(self, idx):
        self.app.article_index = idx
        self.app.goto('article')


class ArticleScreen(Screen):
    def __init__(self, app, name='article', **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.app = app
        root = BoxLayout(orientation='vertical')
        self.topbar = TopBar('', show_back=True,
                             on_back=lambda: self.app.goto('knowledge'))
        root.add_widget(self.topbar)
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        body = BoxLayout(orientation='vertical', size_hint_y=None,
                          spacing=dp(10), padding=[dp(16), dp(12)])
        body.bind(minimum_height=lambda i, v: setattr(i, 'height', v))
        scroll.add_widget(body)
        self.body = body
        root.add_widget(scroll)
        self.add_widget(root)
        self.bind(on_pre_enter=lambda *a: Clock.schedule_once(
            lambda dt: self.show(), 0))

    def _hupd(self, inst, val):
        if hasattr(self, '_hbg'):
            self._hbg.pos = inst.pos
            self._hbg.size = inst.size

    def show(self):
        idx = getattr(self.app, 'article_index', 0)
        art = ARTICLES[idx] if 0 <= idx < len(ARTICLES) else ARTICLES[0]
        self.topbar.title_lbl.text = art['title']
        self.body.clear_widgets()
        head = BoxLayout(orientation='vertical', size_hint_y=None,
                          height=dp(78), spacing=dp(6),
                          padding=[dp(14), dp(12)])
        with head.canvas.before:
            Color(rgba=C(art['color']))
            self._hbg = RoundedRectangle(pos=head.pos, size=head.size,
                                         radius=[dp(16)])
        head.bind(pos=self._hupd, size=self._hupd)
        head.add_widget(L(icons.im(icons.KIND_ICON.get(art.get('kind'), 'heart'))
                          + '  ' + art['title'], 19,
                          '#FFFFFF', bold=True, markup=True))
        head.add_widget(L(art['summary'], 12, (1, 1, 1, 0.9)))
        self.body.add_widget(head)
        card = Card()
        self.body.add_widget(card)
        # 用卡片承载正文
        for sub, para in art['body']:
            card.add_widget(L(sub, 15, theme.PRIMARY, bold=True))
            card.add_widget(L(para, 14, theme.TEXT))
        self.body.add_widget(L('内容仅供健康参考，不构成医疗诊断。',
                               11, theme.TEXT_LIGHT))


# ================= 我的 =================
class ProfileScreen(Screen):
    def __init__(self, app, name='profile', **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.app = app
        root = BoxLayout(orientation='vertical')
        root.add_widget(TopBar('我的'))
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        body = BoxLayout(orientation='vertical', size_hint_y=None,
                          spacing=dp(12), padding=[dp(14), dp(10)])
        body.bind(minimum_height=lambda i, v: setattr(i, 'height', v))
        scroll.add_widget(body)
        root.add_widget(scroll)

        # 外观
        c = Card()
        c.add_widget(L('外观与模式', 15, theme.TEXT, bold=True))
        row = BoxLayout(size_hint_y=None, height=dp(44))
        row.add_widget(L('深色护眼模式', 13, theme.TEXT_LIGHT, size_hint=(1, None)))
        self.sw = Switch(active=theme.is_dark())
        self.sw.bind(active=lambda inst, val: self.app.toggle_theme(val))
        row.add_widget(self.sw)
        c.add_widget(row)
        body.add_widget(c)

        # 数据管理
        c2 = Card()
        c2.add_widget(L('数据管理', 15, theme.TEXT, bold=True))
        c2.add_widget(self._btn('导出 CSV 表格', 'export_csv'))
        c2.add_widget(L('导出后可直接分享到微信 / 邮件', 11,
                        theme.TEXT_LIGHT))
        c2.add_widget(self._btn('本地备份数据库', 'backup_db'))
        c2.add_widget(self._btn('清空全部数据', 'clear_all',
                                color=theme.DANGER))
        body.add_widget(c2)

        # 关于（APP_VERSION 需与 GitHub Release 标签保持一致）
        c3 = Card()
        c3.add_widget(L('关于', 15, theme.TEXT, bold=True))
        c3.add_widget(L('血压记录助手 v%s' % APP_VERSION, 13, theme.TEXT,
                        bold=True))
        c3.add_widget(L('语音 / 键盘双模录入血压；趋势图表与统计分析；\n'
                        '健康知识库。所有数据仅保存在本机，不上传云端，\n'
                        '可导出 CSV 或本地备份，就医时提供给医生参考。',
                        12, theme.TEXT_LIGHT))
        body.add_widget(c3)
        self.add_widget(root)

    def _btn(self, text, method, color=None):
        return B(text, bg=theme.CARD_LIGHT, color=color or theme.TEXT,
                 size=13, height=42, radius=10,
                 on_press=lambda inst, m=method: getattr(self, m)())

    # ---------------- 操作 ----------------
    def export_csv(self):
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = os.path.join(self.app.user_data_dir, 'bp_export_%s.csv' % ts)
        try:
            self.app.db.export_csv(path)
            n = len(self.app.db.get_all())
            shared = False
            try:
                shared = share.share_file(path, title='分享血压数据')
            except Exception:
                shared = False
            if shared:
                message_dialog('导出成功',
                               '已导出 %d 条记录，系统分享面板已打开，\n'
                               '可选择微信、邮件等应用发送。' % n)
            else:
                message_dialog('导出成功',
                               '已导出 %d 条记录：\n%s' % (n, path))
        except Exception as e:
            message_dialog('导出失败', str(e))

    def backup_db(self):
        try:
            p = self.app.db.backup_db()
            message_dialog('备份成功', '备份文件：\n%s' % p)
        except Exception as e:
            message_dialog('备份失败', str(e))

    def clear_all(self):
        def really():
            confirm_dialog('再次确认',
                           '将删除全部血压记录，且无法恢复。\n确定继续吗？',
                           lambda: self._do_clear())
        confirm_dialog('清空全部数据', '此操作会删除所有记录。\n确定继续吗？',
                       really)

    def _do_clear(self):
        self.app.db.delete_all()
        message_dialog('已完成', '所有记录已清空。')
