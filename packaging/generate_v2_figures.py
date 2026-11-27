#!/usr/bin/env python3
"""Generate unified 300 DPI Chinese academic figures for the v2 course report
directly from archived experimental records.

Usage:
  Inside an extracted v2 submission bundle:
    python3 packaging/generate_v2_figures.py
"""
from pathlib import Path
import csv
import json
import math
import statistics

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'report' / 'figures'
OUT.mkdir(parents=True, exist_ok=True)

NAVY = '#1e3a5f'
BLUE = '#2563eb'
TEAL = '#0d9488'
AMBER = '#d97706'
RED = '#dc2626'
SLATE = '#475569'
GRAY = '#94a3b8'


def configure_style():
    font_candidates = [
        '/mnt/c/Windows/Fonts/msyh.ttc',
        'C:/Windows/Fonts/msyh.ttc',
        '/mnt/c/Windows/Fonts/simhei.ttf',
        'C:/Windows/Fonts/simhei.ttf',
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    ]
    zh_font = 'DejaVu Sans'
    for fp in font_candidates:
        if Path(fp).exists():
            font_manager.fontManager.addfont(fp)
            zh_font = font_manager.FontProperties(fname=fp).get_name()
            break

    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': [zh_font, 'DejaVu Sans'],
        'axes.unicode_minus': False,
        'axes.edgecolor': '#334155',
        'axes.linewidth': 0.95,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'grid.color': '#cbd5e1',
        'grid.linestyle': '--',
        'grid.linewidth': 0.6,
        'figure.facecolor': 'white',
        'axes.facecolor': 'white',
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.12,
    })


def draw_box(ax, x, y, w, h, title, desc, bg, edge, title_color=None, fontsize_t=9.5, fontsize_d=8.1):
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle='round,pad=0.06,rounding_size=0.18',
        facecolor=bg, edgecolor=edge, linewidth=1.4,
    )
    ax.add_patch(box)
    ax.text(x + 0.22, y + h - 0.34, title, ha='left', va='top',
            fontsize=fontsize_t, fontweight='bold', color=title_color or edge)
    ax.text(x + 0.22, y + h - 0.76, desc, ha='left', va='top',
            fontsize=fontsize_d, color='#1e293b', linespacing=1.35)


# ---------------------------------------------------------------------------
# Figure 1 (v2): Four-layer cross-layer architecture + v2 Integer Dot dataflow
# ---------------------------------------------------------------------------
def make_v2_arch():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.4, 5.5), gridspec_kw={'width_ratios': [1.05, 1.03]})
    for ax in (ax1, ax2):
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')

    ax1.text(5.0, 9.65, '(a) v1 + v2 四层软硬件跨层优化体系', ha='center', va='center',
             fontsize=11.8, fontweight='bold', color=NAVY)

    layers = [
        ('L4  编译与跨机器运行时自适应层（v1 → v2）', '#eff6ff', BLUE,
         '• 确定性编译：-O3 -mavx2 -mfma -ffp-contract=off\n'
         '• v1 17 模式 + v2 4 组内核/分块(200–203)，按 CPU/源码指纹复用'),
        ('L3  指令集与微架构层（v2 消除全部 512 条 vpsubw）', '#f0fdfa', TEAL,
         '• v1：AVX2 8 通道 + VPMADDWD 平方差 + 1/2/4/8 查询复用\n'
         '• v2：整数范数展开 + VPMADDWD 纯内积恢复，热函数指令 3010 → 2604'),
        ('L2  内存布局与缓存分块层（v2 缓存感知分块）', '#fffbeb', AMBER,
         '• 8 路 AoSoA 交错 + 64B 对齐 + 0–255 无损 uint8（体积降 4×）\n'
         '• v2：预存数据库范数（+3.81 MiB/1M）+ 分块 {128, 256, 512} 自适应'),
        ('L1  算法与数据结构层', '#fef2f2', RED,
         '• 完整排序 O(N log N) → 流式定长最大堆 O(N log K)\n'
         '• 消除 O(N) 距离数组写回，合并单次下沉与 SIMD 掩码剪枝'),
    ]

    ys = [7.55, 5.20, 2.85, 0.50]
    h = 1.70
    for idx, ((title, bg, edge, desc), y) in enumerate(zip(layers, ys)):
        draw_box(ax1, 0.25, y, 9.5, h, title, desc, bg, edge, fontsize_t=9.4, fontsize_d=8.0)
        if idx < len(ys) - 1:
            arr = FancyArrowPatch((5.0, y - 0.05), (5.0, ys[idx + 1] + h + 0.06),
                                  arrowstyle='<|-|>', mutation_scale=11, color=SLATE, linewidth=1.1)
            ax1.add_patch(arr)

    ax2.text(5.0, 9.65, '(b) v2 整数范数展开与 AVX2 整数内积数据流（SIFT1M）', ha='center', va='center',
             fontsize=11.8, fontweight='bold', color=NAVY)

    steps = [
        (7.90, 1.35, '① 索引构建期（一次性）', '#f8fafc', SLATE,
         '行优先 float32 (488.3 MiB) → 8 路 AoSoA uint8 (122.1 MiB) + 预存范数 ‖x‖² (3.81 MiB)'),
        (6.00, 1.40, '② 缓存感知分块与多查询加载（Mode 200/201/202/203）', '#fffbeb', AMBER,
         '按机器选块：Xeon 32 KiB L1D 选 block=128 (16 KiB)；本地大缓存选 block=512 (64 KiB)\n'
         '一次载入参考块供 8 条查询共享，同步计算查询范数 ‖q‖²'),
        (3.85, 1.65, '③ AVX2 无损整数内积与精确 L2 恢复（零 vpsubw）', '#f0fdfa', TEAL,
         'vpmovzxbw 零扩展 16B → vpmaddwd 直接累加 x·q（跳过 512 条坐标相减指令）\n'
         '精确整数恢复：‖x-q‖² = ‖x‖² + ‖q‖² - 2(x·q) ≤ 8,323,200 < 2²⁴（转 float32 零舍入）'),
        (1.90, 1.40, '④ SIMD 阈值掩码剪枝 + 流式最大堆', '#fef2f2', RED,
         'AVX2 比较 + _mm256_movemask_ps 过滤绝大多数非近邻候选\n'
         '仅命中掩码的候选执行单次下沉更新定长堆（字典序唯一确定 ID）'),
        (0.35, 1.05, '⑤ 安全回退保障与 Z3 形式化验证闭环', '#eff6ff', BLUE,
         '非整数 / 浮点(GloVe25) / 小批量自动走原 AoSoA 路径；Z3 证明 36+4+5 项无溢出'),
    ]
    for idx, (y, hh, title, bg, edge, desc) in enumerate(steps):
        draw_box(ax2, 0.25, y, 9.5, hh, title, desc, bg, edge, fontsize_t=9.2, fontsize_d=7.85)
        if idx < len(steps) - 1:
            ny, nh = steps[idx + 1][0], steps[idx + 1][1]
            arr = FancyArrowPatch((5.0, y - 0.04), (5.0, ny + nh + 0.05),
                                  arrowstyle='-|>', mutation_scale=12, color=NAVY, linewidth=1.25)
            ax2.add_patch(arr)

    fig.tight_layout()
    fig.savefig(OUT / 'v2_arch.png')
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 4 (v2): Large-batch profiling, static instruction drop, kernel gain
# ---------------------------------------------------------------------------
def make_v2_kernel_gain():
    # Read profiling shares (period=128)
    def load_profile(path):
        rows = list(csv.DictReader(path.open(encoding='utf-8')))
        out = {}
        for r in rows:
            if int(r['period']) == 128 and r['label'].startswith(('sift1m_q128', 'sift1m_q256')):
                out[r['label'].replace('sift1m_', '').replace('_mode7', '')] = float(r['distance_sample_share']) * 100.0
        return out

    loc_prof = load_profile(ROOT / 'experiments/v2/evidence/local-20261127/local_profile_v1/summary.csv')
    srv_prof = load_profile(ROOT / 'experiments/v2/evidence/server-20261127/server_profile_v1/summary.csv')

    # Read static instruction counts
    inst = json.loads((ROOT / 'experiments/v2/evidence/local-20261127/static_instruction_counts.json').read_text(encoding='utf-8'))
    byte_cnt = dot_cnt = None
    for item in inst:
        ic = item['instruction_counts']
        if sum(ic.values()) < 50:
            continue
        if 'byte128_search<8, 1>' in item['function']:
            byte_cnt = (sum(ic.values()), ic.get('vpsubw', 0))
        elif 'dot128_search<8, 1>' in item['function']:
            dot_cnt = (sum(ic.values()), ic.get('vpsubw', 0))

    # Read confirmation.json for both hosts
    loc_conf = json.loads((ROOT / 'experiments/v2/evidence/local-20261127/local_screen_v2/confirmation.json').read_text(encoding='utf-8'))
    srv_conf = json.loads((ROOT / 'experiments/v2/evidence/server-20261127/server_screen_v1/confirmation.json').read_text(encoding='utf-8'))

    cfgs = ['q128_k1', 'q128_k100', 'q256_k10', 'q256_k100']
    cfg_labels = ['Q128/K1', 'Q128/K100', 'Q256/K10', 'Q256/K100']

    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.1), gridspec_kw={'width_ratios': [1.05, 1.0, 1.0]})

    # Panel (a): Distance share (%) + Static instruction badge
    ax = axes[0]
    x = np.arange(len(cfgs))
    w = 0.34
    loc_shares = [loc_prof[c] for c in cfgs]
    srv_shares = [srv_prof[c] for c in cfgs]
    b1 = ax.bar(x - w / 2, loc_shares, width=w, color=BLUE, label='本机 Core Ultra 9 275HX')
    b2 = ax.bar(x + w / 2, srv_shares, width=w, color=AMBER, label='服务器 Xeon Gold 6133')
    for bars in (b1, b2):
        for bar in bars:
            v = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, v + 1.0, f'{v:.1f}%',
                    ha='center', va='bottom', fontsize=7.6, color='#1e293b')
    ax.set_ylim(0, 108)
    ax.set_xticks(x)
    ax.set_xticklabels(cfg_labels, fontsize=8.5)
    ax.set_ylabel('距离累加抽样耗时占比 (%)', fontsize=9.2)
    ax.set_title('(a) v1 大批量瓶颈定位（距离计算主导）', fontsize=10.2, fontweight='bold', color=NAVY, pad=8)
    ax.grid(axis='y', alpha=0.4)
    ax.legend(loc='lower right', fontsize=8.0, frameon=True, facecolor='white', framealpha=0.92)
    ax.text(0.5, 0.94,
            f'静态指令实测（8查询展开核）：vpsubw {byte_cnt[1]} → {dot_cnt[1]}（总指令 {byte_cnt[0]} → {dot_cnt[0]}）',
            transform=ax.transAxes, ha='center', va='top', fontsize=7.5,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#fef2f2', edgecolor=RED, linewidth=0.8),
            color='#991b1b')

    # Panels (b) & (c): Old custom vs v2 Integer Dot latency
    for ax, rows, title in [
        (axes[1], loc_conf, '(b) 本机：旧自研核 vs v2 整数内积核'),
        (axes[2], srv_conf, '(c) 服务器：旧自研核 vs v2 整数内积核'),
    ]:
        old_ms = [statistics.median([r['base_ms'] for r in rows if r['label'] == f'sift1m_{c}']) for c in cfgs]
        new_ms = [statistics.median([r['selected_ms'] for r in rows if r['label'] == f'sift1m_{c}']) for c in cfgs]
        gains = [o / n for o, n in zip(old_ms, new_ms)]

        ax.bar(x - w / 2, old_ms, width=w, color=GRAY, label='旧自研核 (v1 mode 7)')
        b_new = ax.bar(x + w / 2, new_ms, width=w, color=TEAL, label='v2 整数内积核')
        ymax = max(old_ms) * 1.24
        ax.set_ylim(0, ymax)
        for i_bar, (bar, g) in enumerate(zip(b_new, gains)):
            top_y = max(old_ms[i_bar], new_ms[i_bar])
            ax.text(x[i_bar], top_y + ymax * 0.025, f'{g:.2f}×',
                    ha='center', va='bottom', fontsize=8.3, fontweight='bold', color=NAVY)
        ax.set_xticks(x)
        ax.set_xticklabels(cfg_labels, fontsize=8.5)
        ax.set_ylabel('批次搜索耗时 (ms，越低越好)', fontsize=9.0)
        ax.set_title(title, fontsize=10.2, fontweight='bold', color=NAVY, pad=8)
        ax.grid(axis='y', alpha=0.4)
        ax.legend(loc='upper left', fontsize=8.0, frameon=True, facecolor='white', framealpha=0.92)

    fig.tight_layout()
    fig.savefig(OUT / 'v2_kernel_gain.png')
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 5 (v2): All 26 configs dual-host speedup (v2 bars + same-round v1 markers)
# ---------------------------------------------------------------------------
def make_v2_all_configs():
    fig, axes = plt.subplots(2, 1, figsize=(12.6, 6.8), sharex=True)

    specs = [
        ('local', '(a) 本机 Intel Core Ultra 9 275HX（78/78 领先，几何平均 2.488×，峰值 7.356×）', 8.3),
        ('server', '(b) 学校服务器 Intel Xeon Gold 6133（78/78 领先，几何平均 1.512×，最小 1.085×）', 2.75),
    ]
    labels_ref = None
    for ax, (machine, title, ymax) in zip(axes, specs):
        p = ROOT / f'experiments/v2/evidence/integrated-{machine}-20261127/run/faiss78/summary.csv'
        rows = list(csv.DictReader(p.open(encoding='utf-8')))
        labels = list(dict.fromkeys(r['label'].rsplit('_b', 1)[0] for r in rows))
        labels_ref = labels
        v2_vals = [[float(r['gain']) for r in rows if r['label'].rsplit('_b', 1)[0] == s] for s in labels]
        v1_vals = [[float(r['best_faiss_ms']) / float(r['original_ms']) for r in rows if r['label'].rsplit('_b', 1)[0] == s] for s in labels]

        mid = np.median(v2_vals, axis=1)
        low = np.min(v2_vals, axis=1)
        high = np.max(v2_vals, axis=1)
        v1_mid = np.median(v1_vals, axis=1)

        xs = np.arange(len(labels))
        colors_bar = [TEAL if s.startswith('glove') else BLUE for s in labels]

        # Plot bars cleanly separated for legend
        g_idx = [i for i, s in enumerate(labels) if s.startswith('glove')]
        s_idx = [i for i, s in enumerate(labels) if s.startswith('sift')]
        ax.bar(xs[g_idx], mid[g_idx], width=0.72, color=TEAL, alpha=0.90, label='GloVe25（v2 自动校准）')
        ax.bar(xs[s_idx], mid[s_idx], width=0.72, color=BLUE, alpha=0.90, label='SIFT1M（v2 自动校准）')
        ax.errorbar(xs, mid, yerr=[mid - low, high - mid], fmt='none',
                    color='#0f172a', capsize=2.2, linewidth=0.9, zorder=4)
        ax.scatter(xs, v1_mid, marker='D', s=26, facecolor='#fef3c7', edgecolor=AMBER,
                   linewidth=1.1, zorder=5, label='同轮原固定分派（v1 mode 7）')
        ax.axhline(1.0, color=RED, linestyle='--', linewidth=1.15, zorder=3, label='与最快 Faiss 持平 (1.0×)')

        # Vertical divider between GloVe25 and SIFT1M
        ax.axvline(6.5, color='#94a3b8', linestyle=':', linewidth=1.0)

        # Annotate selected key bars
        for i, m_val in enumerate(mid):
            if machine == 'local' and (m_val >= 3.0 or i >= 22):
                ax.text(xs[i], high[i] + 0.14, f'{m_val:.2f}×', ha='center', va='bottom',
                        fontsize=7.1, color=NAVY, fontweight='bold')
            elif machine == 'server' and (i in (7, 8, 9, 12, 13, 14, 19, 23, 24, 25)):
                ax.text(xs[i], high[i] + 0.045, f'{m_val:.2f}×', ha='center', va='bottom',
                        fontsize=7.1, color=NAVY, fontweight='bold')

        if machine == 'server':
            # Highlight the large-batch configs where block=128 is consistently chosen
            ax.axvspan(18.5, 25.5, color='#fef2f2', alpha=0.45, zorder=0)
            ax.text(22.0, 2.48, 'SIFT 大批量区间（全部选用 block=128）\n由同轮原分派 0.92–1.05× 提升至 1.09–1.26×',
                    ha='center', va='top', fontsize=8.0, color='#991b1b',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=RED, linewidth=0.8))

        ax.set_ylim(0, ymax)
        ax.set_ylabel('相对最快 Faiss 加速比', fontsize=9.5)
        ax.set_title(title, loc='left', fontsize=10.6, fontweight='bold', color=NAVY, pad=6)
        ax.grid(axis='y', alpha=0.35)
        ax.legend(loc='upper right' if machine == 'local' else 'upper left',
                  ncol=2, fontsize=8.1, frameon=True, facecolor='white', framealpha=0.92)

    tick_labels = [
        s.replace('glove25_q', 'G:Q').replace('sift1m_q', 'S:Q').replace('_k', '/K')
        for s in labels_ref
    ]
    axes[-1].set_xticks(np.arange(len(labels_ref)))
    axes[-1].set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=8.4)
    axes[-1].set_xlabel('负载与查询/近邻配置（G 表示 GloVe25，S 表示 SIFT1M）', fontsize=9.5)

    fig.tight_layout()
    fig.savefig(OUT / 'v2_all_configs.png')
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 6 (v2): Automated reproduction pipeline + dual-host amortization
# ---------------------------------------------------------------------------
def make_v2_pipeline_amortization():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 4.7), gridspec_kw={'width_ratios': [1.05, 1.05]})

    # Left: v2 Automated Pipeline
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 10)
    ax1.axis('off')
    ax1.text(5.0, 9.65, '(a) v2 全自动复现与指纹复用流水线（bash reproduce.sh）',
             ha='center', va='center', fontsize=10.8, fontweight='bold', color=NAVY)

    pipe_steps = [
        (8.22, 1.00, '1. 环境预检与依赖准备', '#f8fafc', SLATE,
         '校验 AVX2/FMA、GCC、Python/Faiss/Z3 与单线程绑核约束'),
        (6.82, 1.00, '2. 编译与回归 + 三组 Z3 形式化验证', '#f0fdfa', TEAL,
         '4 组集成回归 + SIFTsmall 48 项；Z3 验证 36 Top-K + 4 字节 + 5 整数内积'),
        (5.37, 1.05, '3. 随包离线数据准备（三份原始负载免下载）', '#fffbeb', AMBER,
         '本地 SHA256 校验解压 SIFTsmall/SIFT1M，float64 归一化生成 GloVe25'),
        (3.52, 1.45, '4. 按机自动校准 / SHA256 指纹复用（26 配置）', '#eff6ff', BLUE,
         '新机首次测量并冻结策略（本机 770s / 服务器 1669s）；\n指纹命中直接复用（本机 7.4s / 服务器 13.7s）'),
        (1.92, 1.15, '5. 78 项同轮随机交错 Faiss 对照（完整模式）', '#fef2f2', RED,
         '26 配置 × 3 批 × 7 次交替，同步核验 SIFT 零误差与 GloVe 容差'),
        (0.32, 1.15, '6. 自动出图、渲染本机 PDF 与打包证据', '#f8fafc', NAVY,
         '输出 SUCCESS.json、performance.json、reproduction_report.pdf 与证据 ZIP'),
    ]
    for idx, (y, hh, title, bg, edge, desc) in enumerate(pipe_steps):
        draw_box(ax1, 0.25, y, 9.5, hh, title, desc, bg, edge, fontsize_t=8.8, fontsize_d=7.55)
        if idx < len(pipe_steps) - 1:
            ny, nh = pipe_steps[idx + 1][0], pipe_steps[idx + 1][1]
            arr = FancyArrowPatch((5.0, y - 0.04), (5.0, ny + nh + 0.04),
                                  arrowstyle='-|>', mutation_scale=11, color=NAVY, linewidth=1.15)
            ax1.add_patch(arr)

    # Right: Dual-host cumulative latency amortization (SIFT1M Q=128, K=100)
    loc_setup = json.loads((ROOT / 'experiments/v2/evidence/integrated-local-20261127/run/faiss78/setup.json').read_text(encoding='utf-8'))['sift1m']
    srv_setup = json.loads((ROOT / 'experiments/v2/evidence/integrated-server-20261127/run/faiss78/setup.json').read_text(encoding='utf-8'))['sift1m']

    def median_q128_k100(machine):
        rows = list(csv.DictReader((ROOT / f'experiments/v2/evidence/integrated-{machine}-20261127/run/faiss78/summary.csv').open(encoding='utf-8')))
        sub = [r for r in rows if r['dataset'] == 'sift1m' and int(r['q']) == 128 and int(r['k']) == 100]
        return statistics.median(float(r['custom_ms']) for r in sub) / 1000.0, statistics.median(float(r['best_faiss_ms']) for r in sub) / 1000.0

    loc_v2_s, loc_fb_s = median_q128_k100('local')
    srv_v2_s, srv_fb_s = median_q128_k100('server')

    batches = np.arange(0, 36)
    loc_v2_tot = loc_setup['adaptive_seconds'] + batches * loc_v2_s
    loc_fb_tot = loc_setup['faiss_flat_seconds'] + batches * loc_fb_s
    srv_v2_tot = srv_setup['adaptive_seconds'] + batches * srv_v2_s
    srv_fb_tot = srv_setup['faiss_flat_seconds'] + batches * srv_fb_s

    ax2.plot(batches, srv_fb_tot, color='#94a3b8', linestyle='--', linewidth=1.8, label='服务器 Faiss BLAS（建库 + 查询）')
    ax2.plot(batches, srv_v2_tot, color=AMBER, linewidth=2.1, label='服务器 自研 v2（建库 + 查询）')
    ax2.plot(batches, loc_fb_tot, color='#64748b', linestyle=':', linewidth=1.8, label='本机 Faiss BLAS（建库 + 查询）')
    ax2.plot(batches, loc_v2_tot, color=TEAL, linewidth=2.1, label='本机 自研 v2（建库 + 查询）')

    # Break-even markers
    loc_be = (loc_setup['adaptive_seconds'] - loc_setup['faiss_flat_seconds']) / (loc_fb_s - loc_v2_s)
    srv_be = (srv_setup['adaptive_seconds'] - srv_setup['faiss_flat_seconds']) / (srv_fb_s - srv_v2_s)
    loc_be_y = loc_setup['adaptive_seconds'] + loc_be * loc_v2_s
    srv_be_y = srv_setup['adaptive_seconds'] + srv_be * srv_v2_s

    ax2.scatter([loc_be], [loc_be_y], color=TEAL, s=48, zorder=6, edgecolor='white', linewidth=1.0)
    ax2.scatter([srv_be], [srv_be_y], color=AMBER, s=48, zorder=6, edgecolor='white', linewidth=1.0)
    ax2.annotate(f'本机回本：约 {math.ceil(loc_be)} 批\n（包装建库差 0.96s）',
                 xy=(loc_be, loc_be_y), xytext=(loc_be + 3.0, loc_be_y + 4.4),
                 arrowprops=dict(arrowstyle='->', color=TEAL, lw=1.1),
                 fontsize=8.1, color='#0f766e', fontweight='bold',
                 bbox=dict(boxstyle='round,pad=0.25', facecolor='#f0fdfa', edgecolor=TEAL, lw=0.8))
    ax2.annotate(f'服务器回本：约 {math.ceil(srv_be)} 批\n（包装建库差 2.83s）',
                 xy=(srv_be, srv_be_y), xytext=(srv_be + 1.2, srv_be_y - 6.8),
                 arrowprops=dict(arrowstyle='->', color=AMBER, lw=1.1),
                 fontsize=8.1, color='#b45309', fontweight='bold',
                 bbox=dict(boxstyle='round,pad=0.25', facecolor='#fffbeb', edgecolor=AMBER, lw=0.8))

    ax2.set_title('(b) SIFT1M（Q=128, K=100）建索引 + 持续查询累计耗时摊销',
                  fontsize=10.5, fontweight='bold', color=NAVY, pad=8)
    ax2.set_xlabel('累计查询批次数（每批 Q=128 条查询）', fontsize=9.2)
    ax2.set_ylabel('累计总耗时（秒，含建索引）', fontsize=9.2)
    ax2.set_xlim(0, 35)
    ax2.set_ylim(0, max(srv_fb_tot) * 1.08)
    ax2.grid(alpha=0.35)
    ax2.legend(loc='upper left', fontsize=7.9, frameon=True, facecolor='white', framealpha=0.92)

    fig.tight_layout()
    fig.savefig(OUT / 'v2_pipeline_and_amortization.png')
    plt.close(fig)


def main():
    configure_style()
    make_v2_arch()
    make_v2_kernel_gain()
    make_v2_all_configs()
    make_v2_pipeline_amortization()

    sources_md = """# v2 报告配图数据来源与统计口径

以下图表均由 `packaging/generate_v2_figures.py` 直接读取归档实验数据自动生成（300 DPI 中文学术配色），并与 `report/figures/SOURCES.md` 中的 v1 历史剖析与路径切换图共同构成完整报告配图体系：

1. `v2_arch.png`：v1+v2 四层软硬件跨层架构与 v2 整数范数展开/AVX2 内积数据流；静态指令数源自 `experiments/v2/evidence/local-20261127/static_instruction_counts.json`，索引载荷源自 `setup_v1/summary.json`。
2. `v2_kernel_gain.png`：
   - (a) 大批量分段抽样距离计算占比（周期 128）：源自 `experiments/v2/evidence/local-20261127/local_profile_v1/summary.csv` 与 `server-20261127/server_profile_v1/summary.csv`；静态指令数源自 `static_instruction_counts.json`。
   - (b)/(c) 双机四重点配置旧自研核与 v2 整数内积核耗时对比（三批中位耗时的中位数）：源自 `local_screen_v2/confirmation.json` 与 `server_screen_v1/confirmation.json`。
3. `v2_all_configs.png`：双机全部 26 配置（78 项）v2 自动校准相对最快适用 Faiss 的三批加速比中位数与极值误差线，叠加同轮原固定分派（`original_ms`）对照点；源自 `integrated-local-20261127/run/faiss78/summary.csv` 与 `integrated-server-20261127/run/faiss78/summary.csv`。
4. `v2_pipeline_and_amortization.png`：
   - (a) `bash reproduce.sh` v2 全自动复现与指纹复用流水线；校准与复用时间源自双机 `steps.json`。
   - (b) 双机 SIFT1M（Q=128, K=100）建索引 + 持续查询累计耗时摊销曲线；建索引耗时源自双机 `faiss78/setup.json`，批次查询耗时源自双机 `faiss78/summary.csv` 三批中位数。
"""
    (OUT / 'V2_SOURCES.md').write_text(sources_md, encoding='utf-8')
    print('Generated v2 Chinese 300 DPI figures successfully in:', OUT)


if __name__ == '__main__':
    main()
