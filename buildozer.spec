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
source.include_patterns = assets/*,assets/*/*,data/*,README.md,extra_manifest.xml

# 版本号
version = 1.0

# Python 依赖（Android 端）
# 说明：Android 端语音识别走系统 SpeechRecognizer(pyjnius)，
# speech_recognition 仅用于桌面端测试，不参与 Android 打包。
requirements = python3,kivy==2.2.1,pyjnius

# 屏幕方向
orientation = portrait

# 全屏显示：避开 Android 系统导航栏 / 状态栏遮挡底部区域
# （否则底部导航与屏幕最下方控件可能被系统栏盖住而点不中）
fullscreen = 1

# Android 权限
android.permissions = RECORD_AUDIO,INTERNET

# Android API
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b

# 非交互环境下自动接受 SDK 许可证（CI 必需）
android.accept_sdk_license = True

# 额外注入到 AndroidManifest.xml：声明可查询系统语音识别服务，
# 修复 Android 11+ 包可见性导致的语音识别不可用问题
android.extra_manifest_xml = extra_manifest.xml

# 固定 python-for-android 版本。
# master 分支已改用 Python 3.14 构建宿主解释器，与 Kivy 2.2.1 自带的
# Cython 0.29 构建链不兼容（会报 ModuleNotFoundError: No module named 'cgi'）。
p4a.branch = v2024.01.21

# 目标架构：现在手机基本都是 arm64；只留一个可让 APK 体积减半
android.archs = arm64-v8a

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
