[app]

# 应用名称
title = 血压记录助手

# 包名（唯一标识）
package.name = bpassistant

# 包域名
package.domain = com.desic.bpassistant

# 源码目录
source.dir = .

# 打包时包含的文件类型
source.include_exts = py,png,jpg,jpeg,kv,ttf,otf,db,md

# 包含的资源目录
source.include_patterns = assets/*,assets/*/*,data/*,README.md

# 版本号
version = 1.0

# Python 依赖（Android 端）
# 说明：Android 端语音识别走系统 SpeechRecognizer(pyjnius)，
# speech_recognition 仅用于桌面端测试，不参与 Android 打包。
requirements = python3,kivy==2.2.1,pyjnius

# 屏幕方向
orientation = portrait

# 不全屏
fullscreen = 0

# Android 权限
android.permissions = RECORD_AUDIO,INTERNET

# Android API
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b

# 目标架构（安卓手机通常为 arm64-v8a）
android.archs = arm64-v8a,armeabi-v7a

# 允许访问外部存储（导出 CSV 到下载目录时可选）
# android.permissions = RECORD_AUDIO,INTERNET,WRITE_EXTERNAL_STORAGE

# 图标与启动图（可选，把文件放到项目根目录后取消注释）
# icon.filename = %(source.dir)s/assets/icon.png
# presplash.filename = %(source.dir)s/assets/presplash.png

[buildozer]

# 日志级别
log_level = 2

# 警告以 root 运行
warn_on_root = 1
