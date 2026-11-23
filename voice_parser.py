# -*- coding: utf-8 -*-
"""
语音/文本解析模块
支持识别：
  - "高压120，低压80，脉搏70"
  - "高压一百二，低压八十，脉搏七十二"
  - "收缩压120 / 舒张压80 / 心率72"
"""

import re

CN_DIGITS = {
    '零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
}
CN_UNITS = {'十': 10, '百': 100, '千': 1000}

# 字段关键词
SYS_KEYS = ['高压', '收缩压', '高压值', '上压', '高压数']
DIA_KEYS = ['低压', '舒张压', '下压', '低压值']
PUL_KEYS = ['脉搏', '心率', '心跳', '脉率', '心跳次数']


def cn_to_num(text):
    """把中文数字（0~9999）转成 int；纯阿拉伯数字也支持"""
    text = text.strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)

    # 处理 "一百二" / "一百二十" / "八十" / "七十二" 等
    total = 0
    current = 0
    has_digit = False
    for ch in text:
        if ch in CN_DIGITS:
            current = CN_DIGITS[ch]
            has_digit = True
        elif ch in CN_UNITS:
            unit = CN_UNITS[ch]
            if current == 0:
                current = 1
            total += current * unit
            current = 0
            has_digit = True
    total += current
    return total if has_digit else None


def _extract_after_keyword(text, keywords):
    """在文本中查找关键词，返回关键词之后的数字"""
    for kw in keywords:
        idx = text.find(kw)
        if idx >= 0:
            rest = text[idx + len(kw):]
            # 跳过常见连接词
            rest = rest.lstrip('：:是约为 大概 大约 ')
            # 先找阿拉伯数字
            m = re.search(r'\d+', rest)
            if m:
                return int(m.group(0))
            # 再找中文数字
            m = re.search(r'[零一二两三四五六七八九十百千]+', rest)
            if m:
                return cn_to_num(m.group(0))
    return None


def parse_voice_text(text):
    """
    解析语音文本，返回 dict:
      {'systolic': int|None, 'diastolic': int|None, 'pulse': int|None, 'raw': text}
    """
    if not text:
        return {'systolic': None, 'diastolic': None, 'pulse': None, 'raw': text}

    t = text.replace('，', ',').replace('。', '.').replace('、', ',')
    # 全角数字转半角
    trans = str.maketrans('０１２３４５６７８９', '0123456789')
    t = t.translate(trans)

    systolic = _extract_after_keyword(t, SYS_KEYS)
    diastolic = _extract_after_keyword(t, DIA_KEYS)
    pulse = _extract_after_keyword(t, PUL_KEYS)

    # 兜底：如果没识别到关键词，尝试按顺序解析三个数字
    if systolic is None and diastolic is None and pulse is None:
        nums = re.findall(r'\d+', t)
        if len(nums) >= 3:
            systolic, diastolic, pulse = int(nums[0]), int(nums[1]), int(nums[2])
        elif len(nums) == 2:
            systolic, diastolic = int(nums[0]), int(nums[1])

    return {
        'systolic': systolic,
        'diastolic': diastolic,
        'pulse': pulse,
        'raw': text,
    }


def validate(systolic, diastolic, pulse):
    """
    数据校验，返回 list of warning messages（空列表表示完全正常）
    注意：只提示，不强制阻止保存。
    """
    warnings = []
    if systolic is None or diastolic is None or pulse is None:
        warnings.append('数据不完整，请检查高压、低压、脉搏是否都填写。')
        return warnings

    try:
        s, d, p = int(systolic), int(diastolic), int(pulse)
    except (ValueError, TypeError):
        warnings.append('数值格式不正确。')
        return warnings

    if s <= 0 or d <= 0 or p <= 0:
        warnings.append('数值必须大于 0。')

    if s <= d:
        warnings.append('高压应大于低压，请确认是否填反。')

    if s < 70 or s > 260:
        warnings.append(f'高压 {s} mmHg 超出常见范围（70~260），请确认。')
    if d < 40 or d > 180:
        warnings.append(f'低压 {d} mmHg 超出常见范围（40~180），请确认。')
    if p < 30 or p > 220:
        warnings.append(f'脉搏 {p} 次/分超出常见范围（30~220），请确认。')

    # 血压分级提示
    if s >= 140 or d >= 90:
        warnings.append('提示：该读数属于高血压范围，建议关注并咨询医生。')
    elif s <= 90 or d <= 60:
        warnings.append('提示：该读数偏低，如有不适请关注。')

    return warnings


def format_record(record):
    """格式化一条记录用于显示"""
    return {
        'id': record['id'],
        'time': record['measure_time'],
        'systolic': record['systolic'],
        'diastolic': record['diastolic'],
        'pulse': record['pulse'],
        'note': record['note'] or '',
    }
