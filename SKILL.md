---
name: park-sandbox
description: Use when 需求是 Web 端可嵌入 3D 态势沙盘/数据可视化组件——园区、工厂、仓库、门店的"全园一张图""态势一张图"、数字孪生 3D 大屏、等距 3D 沙盘、可嵌入现有中台的 three.js 单文件组件（零模型文件、数据驱动、gzip 极小）。触发词：3D沙盘、态势沙盘、园区可视化、park sandbox、embeddable three.js 3D。
---

# park-sandbox · Web 3D 态势沙盘封装

## Overview

**核心原则：代码即模型。** 零 glTF/fbx/obj 模型文件，全部用 three.js 基础几何体（Box/Cylinder/Cone/Sphere）参数化拼装，"每栋楼/每棵树"只是数组里的一行数据。场景是**算出来的，不是建出来的**——数据层一换，沙盘即活。

视觉基准（成品目标效果）：`reference-render.jpg`——等距俯视沙盘、CSS2D 中文标签、三级状态色、空中链路流光、告警呼吸环、底部数据 chips。
实测基准：2026-09-21 FDE 实战松玄蕴战队交付物，单文件 ESM 724KB（gzip 170KB），全场景 <90 draw calls，Playwright 实测零 JS 错误。

## When to Use / When NOT

**用**：嵌入客户中台的态势沙盘、等距 3D 数据可视化、"一张图"指挥中心、需要状态实时驱动的 3D 场景、AI 可维护的轻量 3D。

**不用**：
- 照片级写实渲染（走 glTF+PBR 贴图或 UE，本 skill 的无贴图路线达不到）
- 客户已有 BIM/CAD 需精确保真还原（本路线是抽象示意，不是测绘）
- 纯 2D 平面图就能满足的需求（YAGNI，别为炫技上 3D）

## 技术决策（每条都有 Why，勿随意推翻）

| 决策 | 做法 | Why |
| --- | --- | --- |
| 程序化建模 | 楼=Box 堆叠退台、树=Cone+Cylinder、湖=扁 Cylinder | 文件 170KB vs 模型几 MB；数据驱动；AI 可直接写改维护 |
| 标签 | `CSS2DRenderer` 把 DOM 钉在 3D 坐标 | 中文清晰不糊；样式用 CSS 随便改；可点选交互 |
| 重复物体 | `InstancedMesh`（树/车/灯一次实例化） | 几百棵树只 3 个 draw call；预算 <90 draw calls 靠它 |
| 链路 | `QuadraticBezierCurve` 空中弧线 + 光点沿曲线参数 t 流动 | 表达数据流向；不写 shader 也有动感 |
| 告警动效 | 半透明环 mesh，半径+透明度随时间正弦插值 | 呼吸/脉冲零成本；主循环 requestAnimationFrame 统一驱动 |
| 入场 | 每栋楼递增 delay，position.y 从地下插值升起 | 错峰动画制造"活"感，演示加分 |
| 交互 | `OrbitControls` 限俯仰角（保沙盘感）+ hover 高亮 + 单击锁定信息卡 | 限俯仰是"沙盘"和"自由 3D"的分水岭，勿放太开 |
| 自适应 | `ResizeObserver` 监听容器 | 嵌入任意中台布局 |
| 打包 | 原生 three.js + TypeScript + Vite，tree-shake 成**单文件 ESM**，CSS 内置注入 | 集成零依赖：`mountParkSandbox(el)` 一句挂载 |
| 性能 | 无贴图、无后处理管线、单方向光阴影（可 `shadow:false` 关） | 低配浏览器流畅；省一次 shadow pass |

## 数据接口规范（接真实数据只改这一层）

```ts
// types.ts —— 场景完全由这四个数组驱动
Building { id, name, pos:[x,z], 占地:[w,d], 层数, 状态:'normal'|'warn'|'alert',
           angle?:弧度(绕y, 每栋独立朝向), 标签?:[{text, type}], 焦点?:bool }
Link     { from, to, 状态 }                      // 空中弧线+流光
Point    { id, pos:[x,z], 类型:'parking'|'gate'|..., 标签:{text,type} }
Chip     { 主数字, 单位, 副文案, 告警?:bool }     // 底部数据条
```

楼高 = 层数 × 2.9m（真实住宅层高），比例与底图地块一致，勿用压扁的"示意图高度"。

**状态色三级体系（默认，客户品牌可整体替换）**：正常 `#0755C9` / 体验预警 `#8B5700` / 设备告警 `#B42318`。状态→颜色只在一处映射，全局一致。

## 模块拆分（src/sandbox/，职责单一）

`types` 数据定义｜`ground` 底板(边界多边形 Extrude)/道路(ribbon)/河流/中央广场/树(Instanced+多边形内撒点)｜`buildings` 楼栋造型/退台/状态描边灯｜`links` 弧线流光｜`pulses` 呼吸脉冲环｜`labels` CSS2D｜`overlay` 图例/角标/chips/信息卡/运镜钮｜`interact` 拾取 hover/锁定｜`park` 场景组装/相机/灯光/主循环/入场动画｜`styles` 内置样式（`psb-` 前缀防污染宿主）

## 从地图截图重建真实布局（配准流程，实战四版教训固化）

业主/客户只给地图截图时，**禁止看图估坐标**（实测连错三版）。唯一正确路线：

1. **先核实图片证据**：逐张确认图里画的是什么，与其声称的来源一致再用。真实案例：一张被当作"PC 端权威地图"的截图，哈希比对会话原始附件后发现是**自家 demo 页的空白截图**，前两版布局全被它带偏。
2. **证据分级**：2D 平面图（无透视畸变，可测量）> 业主口述（栋数/楼号/楼层数以他为准，地图标注常不全）> 3D 倾斜图（只作参考，**禁止**在上量坐标/角度）。
3. **标定比例尺 S（米/像素）**：找图上已知宽度的参照物（城市干道 20~25m、小区主路 7m），再用第二个独立参照物交叉校验，偏差 >15% 重标。
4. **打网格放大测量**：PIL 画 50/100px 网格，按区域裁剪放大 2x，逐栋量「中心 px + 长轴两端 px + 宽度 px」，**每栋朝向独立量**；地块边界沿真实形状逐点描（真实地块极少长方形，常被道路弧切）；被 POI 标记遮住的楼要专门截放大图，宁可标"待确认"也不猜。
5. **脚本换算**：用 `scripts/measure_geo.py`（像素→世界坐标→SandboxData 骨架，自带四项自检：边界为空/栋心出界/角度多样性过低直接 FAIL）。产出粘进 `data.ts`（楼栋/点位）和 `ground.ts`（边界/路网）。
6. **楼层数据**：优先直接问业主（贝壳/链家/安居客有楼栋层数，但反爬严重：登录墙+验证码；百度/Bing 搜小区名会被分词重写，别在搜索上死磕超过 3 次）。

地块为不规则多边形时的实现要点：基座 `THREE.Shape + ExtrudeGeometry`，**`rotateX(Math.PI/2)` 贴地且保持 z+ = 南（`rotateX(-π/2)` 会镜像）**；路网用折线 ribbon（条带网格）；撒树 = 边界多边形 point-in-polygon + 每栋楼旋转矩形避障；滨盛路类弧形界外道路 = 边界点沿外法线偏移的 ribbon。

## 交付形态与 API

```js
import { mountParkSandbox } from './park-sandbox.js'   // 唯一入口，ESM 单文件
const sb = mountParkSandbox(el, { shadow: true, orbitToggle: true })
// 句柄: destroy() / startOrbit(sec=13) / stopOrbit() / focusBuilding('B6'|null) / scene
// 数据刷新: update(next: SandboxData) —— 按 id diff 四数组，只改既有对象属性，勿 destroy+remount
```

## 数据刷新与 adapter（接真实数据必读）

组件**纯数据驱动**，接后端 = 换数据不换场景。三层纪律：

1. **adapter 层注入**：组件内不写死 API 地址/鉴权；集成方 `poll() → adapter(dto) → sb.update(next)`，换客户环境只换 adapter。
2. **update 走 diff**：按 id 比对四数组，仅调用 `setStatus / setActive / setChips` 改既有对象；呼吸环等动效元素**对象池预建**（建好隐藏，setActive 只做显隐+重定位，不增删节点）。
3. **不破坏现场四条**：主循环 requestAnimationFrame 永不重启；入场动画只驱动 position.y，与状态更新互不干扰（刷新落在动画中途不跳变）；刷新失败保留旧数据；相机/灯光/地面/链路几何在 update 路径零触碰。

容器建议 `aspect-ratio: 1000/560` 宽幅；组件完全自适应。集成方无需引任何样式/依赖。

## 验收清单（改完就跑，逐项要证据）

- [ ] Playwright 起本地服务开页，截图 + console 零 error（勿"觉得对"就交付）
- [ ] 入场动画完成后再截（等 4~5s），告警焦点栋信息卡状态正确
- [ ] draw calls <90；树/重复物是 InstancedMesh 而非逐个 new
- [ ] hover 高亮、单击锁定、空白解锁、拖拽旋转、滚轮缩放（俯仰受限）全部可用
- [ ] 容器改尺寸场景自适应（ResizeObserver 生效）
- [ ] `shadow:false` 低配模式可跑
- [ ] gzip 后 ≤200KB；无贴图文件、无外部模型请求
- [ ] 数据刷新实测（若有 update）：mock 源改数据 → 触发刷新 → 断言状态变色且**入场动画未重播**
- [ ] 重建真实场景时：渲染截图与 2D 底图并排人工比对 ≥3 个锚点（边界形状/大门位置/焦点栋朝向），全部对上才算过

## 常见错误（negative 面）

- ❌ 引 glTF/fbx"先有个模型" → 违背本 skill 存在的理由；数据无法驱动，AI 难维护
- ❌ 标签用 Canvas 贴图 → 中文发虚；改样式要重烘焙
- ❌ 每棵树 `new Mesh` → draw calls 爆炸，500 棵就卡
- ❌ 上 Bloom/SSAO 后处理堆效果 → 低配卡死；沙盘清晰度靠光影层次不靠辉光
- ❌ OrbitControls 不限俯仰 → 用户翻到底面，"沙盘感"尽失
- ❌ 楼栋状态色散落在各处写死 → 换品牌色要全文搜索；必须状态→颜色单点映射
- ❌ 交付"源码工程"了事 → 客户要的是单文件组件+README（API/集成/数据接口），README 必须含性能预算与验收口径
- ❌ 演示入口 `index.html` 引 `src/*.ts`（Vite 脚手架默认习惯）→ 浏览器静态打开**无法执行 .ts 必空白**；演示/集成入口只能引构建产物 `dist/*.js`，dev 入口与交付入口必须分离，交付前用静态服务器（非 vite dev）实测一遍
- ❌ 全部楼套同一个 angle → 真实小区每栋朝向不同（斜边界 45°、正南北、东西向并存），逐栋量；统一角度是"没量"的信号
- ❌ 地块当长方形/正方形底板 → 真实地块常被道路弧切成不规则多边形，必须按边界逐点描
- ❌ 用 3D 倾斜视角截图量坐标/角度 → 透视畸变，量出来必然全错；只用 2D 平面图测量
- ❌ 图片自称是什么就信什么 → 先核实图里实际画了什么（假"PC 地图"实为 demo 截图的教训）；拿不准就哈希比对原始附件
- ❌ 看图估坐标/脑补布局 → 必须走配准流程（见上节），脚本换算+自检，坐标来源可复现
- ❌ 楼层数瞎编或搜索死磕 → 先问业主；楼高=层数×2.9m，层数不确定时标估计值并告知

## 路演物料（加分项）

`startOrbit(13)` 环绕运镜一圈（约 13s，俯仰受限自动保持沙盘感）+ Playwright/录屏 = 10~15s 路演视频/动图，配 PPT 用。开场 `focusBuilding(告警栋)` 把镜头焦点交给第一视觉焦点。
