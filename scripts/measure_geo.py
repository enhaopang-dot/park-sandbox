#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""地图截图配准换算器：像素测量 -> park-sandbox 世界坐标 + SandboxData 骨架

适用场景：业主/客户给了小区/园区地图截图，要求 3D 沙盘按真实布局重建。
配套流程见 SKILL.md「从地图截图重建真实布局」。本脚本只做换算与自检，测量值必须人工从图上量取。

用法：
1. 用 PIL 给底图打像素网格（major 50/100px），放大到 2x 逐区域读取坐标
2. 填下面 CONFIG 各段（每栋楼：中心px + 长轴两端px + 宽度px）
3. 跑脚本：输出 world 坐标 JSON + 四项自检（边界闭合/栋心在界内/角度多样性/尺度 sanity）
4. 把 buildings/points 粘进项目 data.ts，boundary/paths 粘进 ground.ts

自检红线（踩过的坑固化）：
- ANGLE_DIVERSITY：全部楼角度差 <0.12 rad 直接报错 —— 真实场景每栋朝向不同，统一角度=没量
- 栋心必须在边界多边形内 —— 防止测量/变换符号错
"""
import json, math, sys

# ===================== CONFIG（按图填写） =====================
S = 0.31            # 米/像素：用已知宽度参照物标定（如城市干道 20~25m），再用第二个参照物（广场直径）交叉校验，偏差>15% 必须重标
CX, CY = 600.0, 560.0   # 世界原点对应的像素点（建议取地块中心）

# 每栋楼: (id, 名称, 中心px, 长轴端点1px, 长轴端点2px, 宽度px, 楼层, 状态)
# ⚠️ 长轴方向=楼朝向，逐栋在图上量，禁止复制别栋的角度
BUILDINGS = [
    # 示例: ('B1', '1 号楼', (105, 770), (35, 835), (175, 705), 60, 26, 'alert'),
]

# 地块边界多边形（顺时针，逐点描；真实地块极少是长方形，别偷懒）
BOUNDARY_PX = [
]

# 内部路网折线（每条一组点）
PATHS_PX = [
]

# 兴趣点（门/河/路/POI 标注位）
POI_PX = {
    # 示例: 'plaza': (670, 662), 'gate_nw': (355, 480),
}
# =============================================================

def w(px, py):
    return [round((px - CX) * S, 1), round((py - CY) * S, 1)]

def angle(a1, a2):
    wx, wz = (a2[0]-a1[0]) * S, (a2[1]-a1[1]) * S
    return round(math.atan2(-wz, wx), 2)   # three.js rotation.y（+z 朝南）

def size(a1, a2, wid_px):
    return [round(math.hypot(a2[0]-a1[0], a2[1]-a1[1]) * S, 1), round(wid_px * S, 1)]

def point_in_polygon(x, z, poly):
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, zi = poly[i]; xj, zj = poly[j]
        if (zi > z) != (zj > z) and x < ((xj-xi)*(z-zi))/(zj-zi) + xi:
            inside = not inside
        j = i
    return inside

def main():
    errs, warns = [], []
    if not BOUNDARY_PX:
        errs.append('BOUNDARY_PX 为空 —— 地块边界必须逐点描，禁止用长方形脑补')
    boundary = [w(x, y) for x, y in BOUNDARY_PX]

    buildings = []
    for bid, name, (cx, cy), a1, a2, wid, fl, st in BUILDINGS:
        buildings.append({'id': bid, 'name': name, 'pos': w(cx, cy),
                          'size': size(a1, a2, wid), 'angle': angle(a1, a2),
                          'floors': fl, 'status': st})
        if boundary and not point_in_polygon(*w(cx, cy), boundary):
            errs.append(f'{bid} 栋心落在边界外 —— 检查测量或 CX/CY')

    if len(buildings) >= 3:
        angs = [b['angle'] for b in buildings]
        if max(angs) - min(angs) < 0.12:
            errs.append('全部楼角度差 <0.12 rad —— 疑似统一角度复制，必须逐栋量朝向')

    if len(buildings) >= 2:
        lens = sorted(max(b['size']) for b in buildings)
        if lens[-1] / max(lens[0], 0.1) > 2.5:
            warns.append('楼长差异 >2.5x —— 确认是否把构筑物/裙楼当成了楼栋')

    paths = [[w(x, y) for x, y in p] for p in PATHS_PX]
    poi = {k: w(x, y) for k, (x, y) in POI_PX.items()}

    print(json.dumps({'S': S, 'buildings': buildings, 'boundary': boundary,
                      'paths': paths, 'poi': poi}, ensure_ascii=False, indent=1))
    for x in warns: print('WARN:', x, file=sys.stderr)
    if errs:
        for x in errs: print('FAIL:', x, file=sys.stderr)
        sys.exit(1)
    print('OK: 自检通过', file=sys.stderr)

if __name__ == '__main__':
    main()
