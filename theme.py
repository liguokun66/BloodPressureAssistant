# -*- coding: utf-8 -*-
"""
主题配色
默认：深色极简（护眼），可在「我的」页一键切换浅色。
"""

PALETTES = {
    True: {
        'BG': '#151824',
        'BG2': '#1E2233',
        'CARD': '#262C40',
        'CARD_LIGHT': '#323A55',
        'ACCENT': '#20263A',
        'NAV_BG': '#1A1E2E',
        'TEXT': '#FFFFFF',
        'TEXT_LIGHT': '#A6AEC4',
        'DIVIDER': '#333A52',
        'PRIMARY': '#4A90D9',
        'PRIMARY_LIGHT': '#7FB8F0',
        'SUCCESS': '#2ED573',
        'WARNING': '#FFC312',
        'ORANGE': '#FF8F2B',
        'DANGER': '#FF4757',
        'LOW': '#54A0FF',
        # 输入框专用（比卡片亮，避免看起来“置灰”）
        'FIELD': '#2E3550',
        'FIELD_BD': '#414B6E',
        'HINT': '#A9B1C8',
    },
    False: {
        'BG': '#EEF2F9',
        'BG2': '#FFFFFF',
        'CARD': '#FFFFFF',
        'CARD_LIGHT': '#F2F5FB',
        'ACCENT': '#EFF3FA',
        'NAV_BG': '#FFFFFF',
        'TEXT': '#181C2A',
        'TEXT_LIGHT': '#5B6378',
        'DIVIDER': '#E1E6F1',
        'PRIMARY': '#2F7FD1',
        'PRIMARY_LIGHT': '#5AA2E8',
        'SUCCESS': '#179954',
        'WARNING': '#C98A00',
        'ORANGE': '#E56A00',
        'DANGER': '#E23A4B',
        'LOW': '#2F7FD1',
        'FIELD': '#FFFFFF',
        'FIELD_BD': '#CFD7E8',
        'HINT': '#7A8398',
    },
}

DARK = True          # 当前是否深色模式
_font_name = None    # 中文字体名

# 全局字号系数（UI 文字普遍偏小，统一放大一点）
FONT_SCALE = 1.15


def _apply():
    """把当前调色板写入模块级变量（供 theme.BG 这种方式使用）"""
    for k, v in PALETTES[DARK].items():
        globals()[k] = v


_apply()


def set_dark(dark=True):
    global DARK
    DARK = bool(dark)
    _apply()


def is_dark():
    return DARK


def set_font(name):
    global _font_name
    _font_name = name


def font():
    return _font_name


def C(c):
    """颜色兼容函数：支持 '#RRGGBB' / '#RGB' / (r,g,b,a) / None"""
    if c is None:
        return (1, 1, 1, 1)
    if isinstance(c, str):
        s = c.strip()
        if s.startswith('#'):
            h = s[1:]
            if len(h) == 3:
                h = ''.join(ch * 2 for ch in h)
            if len(h) >= 6:
                r = int(h[0:2], 16) / 255.0
                g = int(h[2:4], 16) / 255.0
                b = int(h[4:6], 16) / 255.0
                a = int(h[6:8], 16) / 255.0 if len(h) >= 8 else 1.0
                return (r, g, b, a)
        return (1, 1, 1, 1)
    if isinstance(c, (tuple, list)):
        return tuple(c)
    return (1, 1, 1, 1)


# ---------------- 血压分级 ----------------
def bp_level(systolic, diastolic):
    """返回 (颜色key, 中文标签)"""
    try:
        s, d = int(systolic), int(diastolic)
    except Exception:
        return 'TEXT_LIGHT', '--'
    if s < 90 or d < 60:
        return 'LOW', '偏低'
    if s < 120 and d < 80:
        return 'SUCCESS', '正常'
    if s < 140 and d < 90:
        return 'WARNING', '正常高值'
    if s < 160 and d < 100:
        return 'ORANGE', '偏高'
    return 'DANGER', '高血压'


def level_color(systolic, diastolic):
    key, _ = bp_level(systolic, diastolic)
    return globals().get(key, globals()['TEXT'])


def level_text(systolic, diastolic):
    _, txt = bp_level(systolic, diastolic)
    return txt
