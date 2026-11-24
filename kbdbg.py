# -*- coding: utf-8 -*-
"""软键盘 / 语音诊断状态（临时）：main.py、voice.py 在安卓上写入，界面读取显示。"""

KB = {
    'req': 0,      # request_keyboard 被调用次数
    'shown': -1,   # SDL 认为软键盘是否可见：1 是 / 0 否 / -1 未检测
    't': 0.0,      # 最近一次 request_keyboard 的时间戳
    'retry': False,  # 是否已启动重试定时器
    'err': '',     # 补丁自身异常
    'imm': '-',    # InputMethodManager.showSoftInput：1 成功 / 0 返回 false / '-' 未尝试
    'n': 0,        # 重试次数（每 0.5s 一次）
    'svc': '?',    # 系统可用 RecognitionService 数量
    'nw': '?',     # 网络连接：1 通 / 0 不通 / '?' 未知
}
