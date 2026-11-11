#!/usr/bin/env python3
"""
CI（macOS）：把品牌 icon / splash 写入 Capacitor iOS 工程（Assets.xcassets）。

背景：Capacitor 模板自带默认 AppIcon（蓝 X）与默认 Splash；Android 侧有
generate-adaptive-icons.py 处理，iOS 侧此前没有对应步骤，导致装出来的
APP 图标/启动图永远是 Capacitor 默认图。本脚本在 `npx cap add ios` 之后、
`xcodebuild` 之前运行。

依赖：Pillow（workflow 中 pip install）。
"""

import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(ROOT, 'resources')
XCASSETS = os.path.join(ROOT, 'ios', 'App', 'App', 'Assets.xcassets')
APPICON_DIR = os.path.join(XCASSETS, 'AppIcon.appiconset')
SPLASH_DIR = os.path.join(XCASSETS, 'Splash.imageset')

# Capacitor 7 模板 Splash.imageset/Contents.json 的文件名（1x/2x/3x）
SPLASH_FILES = {
    'splash-2732x2732-2.png': 1,
    'splash-2732x2732-1.png': 2,
    'splash-2732x2732.png': 3,
}

SPLASH_CONTENTS_JSON = """{
  "images" : [
    {
      "idiom" : "universal",
      "filename" : "splash-2732x2732-2.png",
      "scale" : "1x"
    },
    {
      "idiom" : "universal",
      "filename" : "splash-2732x2732-1.png",
      "scale" : "2x"
    },
    {
      "idiom" : "universal",
      "filename" : "splash-2732x2732.png",
      "scale" : "3x"
    }
  ],
  "info" : {
    "version" : 1,
    "author" : "xcode"
  }
}
"""


def fail(msg):
    print(f'::error::apply-ios-assets: {msg}')
    sys.exit(1)


def load_icon():
    """优先 resources/icon.png，其次 square-icon.png。"""
    for name in ('icon.png', 'square-icon.png'):
        p = os.path.join(ASSETS_DIR, name)
        if not os.path.exists(p):
            continue
        try:
            im = Image.open(p)
            im.load()
            if im.width > 0 and im.height > 0:
                return im.convert('RGBA'), name
        except Exception as e:  # noqa: BLE001
            print(f'apply-ios-assets: WARN {name} 不可读: {e}')
    return None, None


def square_pad(im):
    """镜像边缘补成正方形（无缝、不变形、不裁切）。"""
    w, h = im.size
    if w == h:
        return im
    side = max(w, h)
    out = Image.new('RGBA', (side, side))
    x0 = (side - w) // 2
    y0 = (side - h) // 2
    out.paste(im, (x0, y0))
    if y0:
        # 顶部空边：镜像原图顶部；不够高就循环镜像
        remaining, src_strip = y0, im.crop((0, 0, w, min(y0, h))).transpose(Image.FLIP_TOP_BOTTOM)
        pos = 0
        while remaining > 0:
            strip = src_strip if src_strip.height <= remaining else src_strip.crop((0, 0, w, remaining))
            out.paste(strip, (x0, pos))
            remaining -= strip.height
            pos += strip.height
        remaining = side - h - y0
        bottom = im.crop((0, max(0, h - min(remaining, h)), w, h)).transpose(Image.FLIP_TOP_BOTTOM)
        pos = h + y0
        while remaining > 0:
            strip = bottom if bottom.height <= remaining else bottom.crop((0, bottom.height - remaining, w, bottom.height))
            out.paste(strip, (x0, pos))
            remaining -= strip.height
            pos += strip.height
    if x0:
        remaining = x0
        left = im.crop((0, 0, min(x0, w), h)).transpose(Image.FLIP_LEFT_RIGHT)
        pos = 0
        while remaining > 0:
            strip = left if left.width <= remaining else left.crop((0, 0, remaining, h))
            out.paste(strip, (pos, y0))
            remaining -= strip.width
            pos += strip.width
        remaining = side - w - x0
        right = im.crop((max(0, w - min(remaining, w)), 0, w, h)).transpose(Image.FLIP_LEFT_RIGHT)
        pos = w + x0
        while remaining > 0:
            strip = right if right.width <= remaining else right.crop((right.width - remaining, 0, right.width, h))
            out.paste(strip, (pos, y0))
            remaining -= strip.width
            pos += strip.width
    return out


def write_appicon():
    icon, src_name = load_icon()
    if icon is None:
        fail('resources/ 下没有可用的 icon.png / square-icon.png')
    icon = square_pad(icon).resize((1024, 1024), Image.LANCZOS)
    if 'A' in icon.getbands():
        rgb = Image.new('RGB', icon.size, (0, 0, 0))
        rgb.paste(icon, mask=icon.getchannel('A'))
        icon = rgb
    os.makedirs(APPICON_DIR, exist_ok=True)
    out_path = os.path.join(APPICON_DIR, 'AppIcon-512@2x.png')
    icon.save(out_path, 'PNG')
    chk = Image.open(out_path)
    chk.load()
    if chk.size != (1024, 1024) or 'A' in chk.getbands():
        fail(f'AppIcon 校验失败: size={chk.size} mode={chk.mode}')
    print(f'apply-ios-assets: AppIcon-512@2x.png 1024x1024 <- resources/{src_name} '
          f'({os.path.getsize(out_path)} bytes)')


def write_splash():
    src_path = os.path.join(ASSETS_DIR, 'splash.png')
    if not os.path.exists(src_path):
        print('apply-ios-assets: WARN resources/splash.png 不存在，保留模板默认启动图')
        return
    os.makedirs(SPLASH_DIR, exist_ok=True)
    with open(os.path.join(SPLASH_DIR, 'Contents.json'), 'w', encoding='utf-8') as f:
        f.write(SPLASH_CONTENTS_JSON)
    im = Image.open(src_path)
    im.load()
    im = im.convert('RGB')
    for name, scale in SPLASH_FILES.items():
        out = im.resize((im.width * scale, im.height * scale), Image.LANCZOS)
        out.save(os.path.join(SPLASH_DIR, name), 'PNG')
        print(f'apply-ios-assets: Splash {name} {out.width}x{out.height} '
              f'({os.path.getsize(os.path.join(SPLASH_DIR, name))} bytes)')


def main():
    if not os.path.isdir(os.path.join(ROOT, 'ios', 'App')):
        fail('ios/App 缺失 — 先运行 npx cap add ios')
    if not os.path.isdir(os.path.join(XCASSETS, 'AppIcon.appiconset')):
        fail(f'模板 AppIcon.appiconset 缺失: {APPICON_DIR}')
    write_appicon()
    if os.environ.get('SPLASH_ENABLED', 'true').strip().lower() == 'false':
        print('apply-ios-assets: SPLASH_ENABLED=false，跳过启动图替换')
    else:
        write_splash()
    print('apply-ios-assets: OK')


if __name__ == '__main__':
    main()
