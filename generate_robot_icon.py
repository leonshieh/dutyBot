"""生成机器人托盘图标"""
from PIL import Image, ImageDraw

size = 64
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# 身体/头部 — 圆角矩形
draw.rounded_rectangle([8, 8, 55, 55], radius=12, fill=(59, 130, 246), outline=(37, 99, 235), width=2)

# 天线
draw.rectangle([28, 2, 35, 10], fill=(37, 99, 235))
draw.ellipse([26, 0, 37, 8], fill=(239, 68, 68))

# 眼睛（白色底 + 深色瞳孔）
draw.ellipse([20, 20, 28, 28], fill=(255, 255, 255))
draw.ellipse([36, 20, 44, 28], fill=(255, 255, 255))
draw.ellipse([22, 22, 26, 26], fill=(30, 41, 59))
draw.ellipse([38, 22, 42, 26], fill=(30, 41, 59))

# 嘴巴 — 微笑的弧线
draw.arc([24, 30, 40, 44], start=0, end=180, fill=(255, 255, 255), width=2)

# 耳朵/侧边
draw.rectangle([2, 24, 8, 30], fill=(99, 102, 241))
draw.rectangle([56, 24, 62, 30], fill=(99, 102, 241))

img.save('web/robot.png')
print('✅ robot.png 已生成！')
