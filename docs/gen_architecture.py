"""生成月下系统架构拓扑图 — 辐射式，以后端服务层为中心"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

# 全局配置
BG_COLOR = '#1a1a2e'
TEXT_COLOR = 'white'
FONT_FAMILY = 'Microsoft YaHei'

plt.rcParams['font.family'] = FONT_FAMILY
plt.rcParams['axes.unicode_minus'] = False

fig, ax = plt.subplots(figsize=(18, 20), dpi=150)
fig.patch.set_facecolor(BG_COLOR)
ax.set_facecolor(BG_COLOR)
ax.set_xlim(0, 18)
ax.set_ylim(0, 20)
ax.axis('off')


def draw_layer_bg(x, y, w, h, color, alpha=0.12, linewidth=1.5):
    """画层背景半透明圆角方块"""
    patch = mpatches.FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.15",
        facecolor=color, alpha=alpha,
        edgecolor=color, linewidth=linewidth
    )
    ax.add_patch(patch)


def draw_box(x, y, w, h, color, text, fontsize=9, bold=False):
    """画小方块并居中文字，返回中心坐标"""
    patch = mpatches.FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.1",
        facecolor=color, alpha=0.85,
        edgecolor='white', linewidth=0.5
    )
    ax.add_patch(patch)
    weight = 'bold' if bold else 'normal'
    ax.text(x + w / 2, y + h / 2, text,
            ha='center', va='center', color=TEXT_COLOR,
            fontsize=fontsize, fontweight=weight)
    return (x + w / 2, y + h / 2)


def draw_arrow(x1, y1, x2, y2, rad=0):
    """画连接箭头"""
    cs = f'arc3,rad={rad}' if rad else 'arc3,rad=0'
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(
                    arrowstyle='->', color='white',
                    alpha=0.5, lw=1.5,
                    connectionstyle=cs
                ))


def draw_row_boxes(items, x_start, x_end, y, box_w, box_h, color, fontsize=9, gap=0.3):
    """在 [x_start, x_end] 范围内居中排列一行方块，返回每个方块的中心坐标"""
    n = len(items)
    total_w = n * box_w + (n - 1) * gap
    offset = x_start + (x_end - x_start - total_w) / 2
    centers = []
    for i, text in enumerate(items):
        bx = offset + i * (box_w + gap)
        cx, cy = draw_box(bx, y, box_w, box_h, color, text, fontsize)
        centers.append((cx, cy))
    return centers


# ============================================================
# 1. 用户层 y=18.5
# ============================================================
c_user = '#9b59b6'
draw_layer_bg(3, 18.0, 12, 1.2, c_user)
ax.text(3.3, 19.0, '用户层', color=TEXT_COLOR, fontsize=11, fontweight='bold')

user_c = draw_box(6.0, 18.2, 1.8, 0.7, c_user, '用户')
browser_c = draw_box(10.2, 18.2, 1.8, 0.7, c_user, '浏览器')
# 用户 → 浏览器
ax.annotate('', xy=(10.2, 18.55), xytext=(7.8, 18.55),
            arrowprops=dict(arrowstyle='->', color='white', alpha=0.8, lw=1.5))

# ============================================================
# 2. 前端层 y=17
# ============================================================
c_fe = '#3498db'
draw_layer_bg(1.5, 16.2, 15, 1.6, c_fe)
ax.text(1.8, 17.55, '前端层', color=TEXT_COLOR, fontsize=11, fontweight='bold')

draw_box(2.5, 17.0, 13, 0.55, c_fe, '前端 SPA (React 19 + Vite 6 + TailwindCSS 4)', fontsize=10, bold=True)
pages = ['首页', '聊天页', '日记页', '配置页', '关于页']
draw_row_boxes(pages, 1.5, 16.5, 16.35, 1.8, 0.5, c_fe, fontsize=8)

# ============================================================
# 3. 通信层 y=15.5
# ============================================================
c_comm = '#1abc9c'
draw_layer_bg(3, 15.0, 12, 0.9, c_comm)
ax.text(3.3, 15.7, '通信层', color=TEXT_COLOR, fontsize=11, fontweight='bold')

comms = ['REST API', 'SSE 流式', 'WebSocket']
comm_centers = draw_row_boxes(comms, 3, 15, 15.1, 2.5, 0.55, c_comm)

# 顶部线性箭头：用户→前端→通信
draw_arrow(9, 18.0, 9, 17.6)
draw_arrow(9, 16.2, 9, 15.65)

# ============================================================
# 4. API 路由层 y=13.5
# ============================================================
c_api = '#27ae60'
draw_layer_bg(2, 13.0, 14, 1.0, c_api)
ax.text(2.3, 13.8, 'API 路由层', color=TEXT_COLOR, fontsize=11, fontweight='bold')

apis = ['chat', 'session', 'config', 'system', 'asr', 'ws']
api_centers = draw_row_boxes(apis, 2, 16, 13.15, 1.6, 0.5, c_api, fontsize=8)

# 通信层 → API层
draw_arrow(9, 15.0, 9, 13.65)

# ============================================================
# 5. 服务层 y=11.5（核心枢纽，加粗边框）
# ============================================================
c_svc = '#2ecc71'
draw_layer_bg(2.5, 11.0, 13, 1.2, c_svc, alpha=0.18, linewidth=2.5)
ax.text(2.8, 12.0, '服务层（系统枢纽）', color=TEXT_COLOR, fontsize=11, fontweight='bold')

svc_items = ['BrainService', 'PerceptionService', 'LogService']
svc_centers = draw_row_boxes(svc_items, 2.5, 15.5, 11.15, 3.2, 0.6, c_svc, fontsize=9)
# svc_centers[0]=BrainService, [1]=PerceptionService, [2]=LogService

# API层 → 服务层
draw_arrow(9, 13.0, 9, 11.75)

# ============================================================
# 6. 核心层（左侧 x=0.5~6.5, y=7~10.5）
# ============================================================
c_core = '#e67e22'
draw_layer_bg(0.5, 7.0, 6.0, 3.5, c_core)
ax.text(0.8, 10.2, '核心层', color=TEXT_COLOR, fontsize=11, fontweight='bold')

core_row1 = ['LLM Engine\n(Transformers)', 'PromptManager']
core_r1 = draw_row_boxes(core_row1, 0.5, 6.5, 8.8, 2.4, 0.7, c_core, fontsize=8, gap=0.3)

core_row2 = ['SessionManager', 'Memory', 'DiaryWriter']
core_r2 = draw_row_boxes(core_row2, 0.5, 6.5, 7.5, 1.7, 0.6, c_core, fontsize=8, gap=0.2)

# 服务层 BrainService → 核心层（左下弧线）
draw_arrow(svc_centers[0][0] - 0.5, svc_centers[0][1] - 0.3, 5.5, 9.5, rad=0.2)

# ============================================================
# 7. 感知层（右侧 x=11.5~17.5, y=7~10.5）
# ============================================================
c_perc = '#e84393'
draw_layer_bg(11.5, 7.0, 6.0, 3.5, c_perc)
ax.text(11.8, 10.2, '感知层', color=TEXT_COLOR, fontsize=11, fontweight='bold')

perc_row1 = ['TTS Client', 'GPT-SoVITS']
perc_r1 = draw_row_boxes(perc_row1, 11.5, 17.5, 8.8, 2.4, 0.7, c_perc, fontsize=8, gap=0.3)
# TTS → GPT-SoVITS 内部箭头
ax.annotate('', xy=(perc_r1[1][0] - 1.2, perc_r1[1][1]), xytext=(perc_r1[0][0] + 1.2, perc_r1[0][1]),
            arrowprops=dict(arrowstyle='->', color='white', alpha=0.6, lw=1.0))

perc_row2 = ['EmotionPool', 'ASR (未集成)']
perc_r2 = draw_row_boxes(perc_row2, 11.5, 17.5, 7.5, 2.4, 0.6, c_perc, fontsize=8, gap=0.3)

# 服务层 PerceptionService → 感知层（右下弧线）
draw_arrow(svc_centers[1][0] + 0.5, svc_centers[1][1] - 0.3, 12.5, 9.5, rad=-0.2)

# ============================================================
# 8. 存储层（底部左侧 x=0.5~6.5, y=3.5~6）
# ============================================================
c_store = '#636e72'
draw_layer_bg(0.5, 3.5, 6.0, 2.5, c_store)
ax.text(0.8, 5.7, '存储层', color=TEXT_COLOR, fontsize=11, fontweight='bold')

store_row1 = ['config.yaml', 'sessions/', 'chromadb/']
store_r1 = draw_row_boxes(store_row1, 0.5, 6.5, 4.8, 1.6, 0.5, c_store, fontsize=8, gap=0.2)

store_row2 = ['tts_output/', 'diary/', 'logs/']
store_r2 = draw_row_boxes(store_row2, 0.5, 6.5, 3.8, 1.6, 0.5, c_store, fontsize=8, gap=0.2)

# 核心层 → 存储层（向下）
draw_arrow(3.5, 7.0, 3.5, 5.3)
# 核心层 SessionManager → sessions/
draw_arrow(core_r2[0][0], core_r2[0][1] - 0.3, store_r1[1][0], store_r1[1][1] + 0.25)
# 核心层 Memory → chromadb/
draw_arrow(core_r2[1][0], core_r2[1][1] - 0.3, store_r1[2][0], store_r1[2][1] + 0.25)
# 服务层 LogService → 存储层 logs/
draw_arrow(svc_centers[2][0], svc_centers[2][1] - 0.3, store_r2[2][0], store_r2[2][1] + 0.25, rad=0.2)

# ============================================================
# 9. 外部服务（底部右侧 x=11.5~17.5, y=3.5~6）
# ============================================================
c_ext = '#f39c12'
draw_layer_bg(11.5, 3.5, 6.0, 2.5, c_ext)
ax.text(11.8, 5.7, '外部服务', color=TEXT_COLOR, fontsize=11, fontweight='bold')

ext_items = ['Qwen3-VL-4B\n(GPU)', 'GPT-SoVITS\n服务 (:9880)']
ext_centers = draw_row_boxes(ext_items, 11.5, 17.5, 4.0, 2.5, 0.8, c_ext, fontsize=8, gap=0.5)

# 核心层 LLM Engine → 外部依赖 Qwen（斜向右下）
draw_arrow(core_r1[0][0] + 1.0, core_r1[0][1] - 0.35, ext_centers[0][0] - 1.0, ext_centers[0][1] + 0.4, rad=0.15)
# 感知层 TTS Client → 外部依赖 GPT-SoVITS（斜向左下）
draw_arrow(perc_r1[0][0], perc_r1[0][1] - 0.35, ext_centers[1][0], ext_centers[1][1] + 0.4, rad=-0.15)

# ============================================================
# 水印
# ============================================================
ax.text(17.5, 0.3, 'YueXia Architecture v0.3.2',
        ha='right', va='bottom', color='white', alpha=0.4,
        fontsize=8, fontstyle='italic')

# 保存
output_path = Path(__file__).parent / 'architecture.png'
plt.tight_layout(pad=0.5)
plt.savefig(output_path, facecolor=BG_COLOR, edgecolor='none', bbox_inches='tight')
plt.close()
print(f"架构图已生成: {output_path}")
