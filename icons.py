# -*- coding: utf-8 -*-
"""
图标字体模块 —— Google Material Icons（Apache License 2.0）
字体文件：assets/icons/MaterialIcons-Regular.ttf
用途：替代 emoji，保证在中文字体下也能正常显示
"""

import os

from kivy.core.text import LabelBase

FONT_NAME = 'MIcon'


def _font_path(*parts):
    """定位 assets 下的字体（兼容桌面与 Android 打包后的路径）"""
    cands = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     'assets', *parts),
        os.path.join(os.getcwd(), 'assets', *parts),
    ]
    for c in cands:
        if os.path.exists(c):
            return c
    return cands[0]


FONT_FILE = _font_path('icons', 'MaterialIcons-Regular.ttf')

# 名称 -> 字形（Material Icons 私有区码点）
GLYPHS = {
    'record':       '\ue745',   # edit_note
    'chart':        '\uf092',   # insights
    'book':         '\uea19',   # menu_book
    'user':         '\ue853',   # account_circle
    'mic':          '\ue029',
    'edit':         '\ue3c9',
    'delete':       '\ue872',
    'add':          '\ue145',
    'heart':        '\ue87d',
    'heart_border': '\ue87e',
    'home':         '\ue88a',
    'waves':        '\ue176',
    'ruler':        '\ue41c',
    'chat':         '\ue0ca',
    'check':        '\ue86c',
    'close':        '\ue5cd',
    'calendar':     '\uebcc',
    'clock':        '\ue8b5',
    'chevron':      '\ue5cc',
    'download':     '\ue2c4',
    'lock':         '\ue897',
    'info':         '\ue88e',
    'warning':      '\ue002',
    'settings':     '\ue8b8',
    'circle':       '\uef4a',
    'blood':        '\uefe4',   # bloodtype
    'scope':        '\ueaa2',   # monitor_heart
}

# 知识库 kind -> 图标名
KIND_ICON = {
    'scope': 'scope',
    'heart': 'heart',
    'wave': 'waves',
    'house': 'home',
    'ruler': 'ruler',
    'chat': 'chat',
}


def register():
    """注册图标字体（失败不致命）"""
    if not os.path.exists(FONT_FILE):
        print('[icons] 字体不存在:', FONT_FILE)
        return False
    try:
        LabelBase.register(FONT_NAME, fn_regular=FONT_FILE)
        return True
    except Exception as e:
        print('[icons] 注册失败:', e)
        return False


def ic(name):
    """返回原始字形字符"""
    return GLYPHS.get(name, '')


def im(name):
    """返回可用于 markup 的字体片段：[font=MIcon]<glyph>[/font]"""
    return '[font=%s]%s[/font]' % (FONT_NAME, ic(name))
