# -*- coding: utf-8 -*-
"""
Android 文件分享。

导出 CSV 后：
  1. 把文件写入系统「下载」目录（MediaStore，Android 10+，无需存储权限）
  2. 通过 ACTION_SEND 调起系统分享面板，可直接发给微信 / 邮件 / 蓝牙等

桌面端（开发调试）直接返回 False，调用方沿用原有提示。
"""

import os


def share_file(path, title='分享文件', mime='text/csv'):
    """分享文件。返回 True 表示已成功调起系统分享面板。"""
    if not path or not os.path.exists(path):
        return False
    try:
        from jnius import autoclass, cast
    except Exception:
        return False

    try:
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        Intent = autoclass('android.content.Intent')
        Build = autoclass('android.os.Build')

        uri = None
        if Build.VERSION.SDK_INT >= 29:
            ContentValues = autoclass('android.content.ContentValues')
            MediaStore = autoclass('android.provider.MediaStore')
            cv = ContentValues()
            cv.put('display_name', os.path.basename(path))
            cv.put('mime_type', mime)
            cv.put('relative_path', 'Download/')
            resolver = activity.getContentResolver()
            uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, cv)
            if uri is not None:
                out = resolver.openOutputStream(uri)
                try:
                    with open(path, 'rb') as f:
                        out.write(f.read())
                finally:
                    try:
                        out.flush()
                        out.close()
                    except Exception:
                        pass

        if uri is None:
            # 老系统或 MediaStore 不可用：退化为文本分享
            with open(path, 'r', encoding='utf-8-sig') as f:
                text = f.read()
            intent = Intent(Intent.ACTION_SEND)
            intent.setType('text/plain')
            intent.putExtra(Intent.EXTRA_SUBJECT, title)
            intent.putExtra(Intent.EXTRA_TEXT, text[:4000])
            chooser = Intent.createChooser(intent, title)
            activity.startActivity(chooser)
            return True

        intent = Intent(Intent.ACTION_SEND)
        intent.setType(mime)
        intent.putExtra(Intent.EXTRA_STREAM,
                        cast('android.os.Parcelable', uri))
        intent.putExtra(Intent.EXTRA_SUBJECT, os.path.basename(path))
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        chooser = Intent.createChooser(intent, title)
        activity.startActivity(chooser)
        return True
    except Exception:
        return False


def share_text(text, title='分享'):
    """纯文本分享（兜底方案）"""
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        Intent = autoclass('android.content.Intent')
        intent = Intent(Intent.ACTION_SEND)
        intent.setType('text/plain')
        intent.putExtra(Intent.EXTRA_TEXT, text[:4000])
        chooser = Intent.createChooser(intent, title)
        activity.startActivity(chooser)
        return True
    except Exception:
        return False
