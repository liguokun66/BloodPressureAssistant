# -*- coding: utf-8 -*-
"""软键盘诊断状态（临时）：main.py 在安卓上打补丁后写入，界面读取显示。"""

KB = {
    'req': 0,      # request_keyboard 被调用次数
    'shown': -1,   # SDL 认为软键盘是否可见：1 是 / 0 否 / -1 未检测
    't': 0.0,      # 最近一次 request_keyboard 的时间戳
    'retry': False,  # 宽限期内是否已尝试重新唤起
    'err': '',     # 补丁自身异常
}
