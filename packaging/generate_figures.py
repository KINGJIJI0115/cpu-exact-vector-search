#!/usr/bin/env python3
"""Generate all 5 academic report figures directly from archived experimental records.

Usage:
  Inside an extracted submission bundle:
    python3 packaging/generate_figures.py
  Or directly against the submission ZIP archive:
    python3 packaging/generate_figures.py --zip 51295903131_赵信喆_系统优化最终提交包.zip --out figures
"""
import argparse
import csv
import io
import json
import math
import statistics
import zipfile
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np


class BundleReader:
    def __init__(self, root: Path = None, zip_path: Path = None):
        self.root = root
        self.zf = zipfile.ZipFile(zip_path, 'r') if zip_path else None

    def read_text(self, rel: str) -> str:
        if self.zf is not None:
            return self.zf.read(rel).decode('utf-8')
        return (self.root / rel).read_text(encoding='utf-8')

    def read_json(self, rel: str):
        return json.loads(self.read_text(rel))

    def read_csv(self, rel: str):
        return list(csv.DictReader(io.StringIO(self.read_text(rel))))

    def close(self):
        if self.zf is not None:
            self.zf.close()


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
        'grid.color': '#cbd5e1',
        'grid.linestyle': '--',
        'grid.linewidth': 0.6,
        'figure.facecolor': 'white',
        'axes.facecolor': 'white',
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.12,
    })


NAVY = '#1e3a5f'
BLUE = '#2563eb'
TEAL = '#0d9488'
AMBER = '#d97706'
RED = '#dc2626'
SLATE = '#475569'
BORDER = '#94a3b8'


# ---------------------------------------------------------------------------
# Figure 1: Four-layer cross-layer architecture + AoSoA / VPMADDWD dataflow
# ---------------------------------------------------------------------------
def make_fig1(out_dir: Path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 5.4), gridspec_kw={'width_ratios': [1.05, 1.02]})
    for ax in (ax1, ax2):
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')

    ax1.text(5.0, 9.65, '(a) 四层软硬件跨层优化体系', ha='center', va='center', fontsize=12.0, fontweight='bold', color=NAVY)

    layers = [
        ('L4  编译与运行时自适应层', '#eff6ff', BLUE,
         '• 确定性编译：-O3 -mavx2 -mfma -ffp-contract=off\n'
         '• 17 模式本机自动校准 + CPU/源码指纹缓存'),
        ('L3  指令集与微架构层 (ISA)', '#f0fdfa', TEAL,
         '• AVX2 8 通道并行 + VPMADDWD 无损整数乘加\n'
         '• 128/25 维展开 + 多查询(1/2/4/8)寄存器复用'),
        ('L2  内存布局与缓存层', '#fffbeb', AMBER,
         '• 8 路 AoSoA 交错 + 64B 对齐 + 256 候选分块\n'
         '• 0–255 整数 uint8 表示（存储体积降 4×）'),
        ('L1  算法与数据结构层', '#fef2f2', RED,
         '• 完整排序 O(N log N) → 流式最大堆 O(N log K)\n'
         '• 消除 O(N) 距离数组，合并为单次下沉调整'),
    ]

    ys = [7.55, 5.20, 2.85, 0.50]
    h = 1.65
    for idx, ((title, bg, edge, desc), y) in enumerate(zip(layers, ys)):
        box = FancyBboxPatch((0.25, y), 9.5, h, boxstyle='round,pad=0.10,rounding_size=0.16',
                             facecolor=bg, edgecolor=edge, linewidth=1.6)
        ax1.add_patch(box)
        bar = FancyBboxPatch((0.25, y), 0.24, h, boxstyle='round,pad=0.0,rounding_size=0.08',
                             facecolor=edge, edgecolor='none')
        ax1.add_patch(bar)
        ax1.text(0.82, y + h - 0.30, title, ha='left', va='center', fontsize=10.4, fontweight='bold', color=edge)
        ax1.text(0.82, y + 0.54, desc, ha='left', va='center', fontsize=9.1, color='#1e293b', linespacing=1.45)
        if idx < len(ys) - 1:
            arr = FancyArrowPatch((5.0, y - 0.14), (5.0, ys[idx + 1] + h + 0.14),
                                  arrowstyle='<->', mutation_scale=11, color=SLATE, linewidth=1.2)
            ax1.add_patch(arr)

    ax2.text(5.0, 9.65, '(b) 8 路 AoSoA 字节布局与 AVX2 数据流', ha='center', va='center', fontsize=12.0, fontweight='bold', color=NAVY)

    b1 = FancyBboxPatch((0.25, 7.65), 9.5, 1.45, boxstyle='round,pad=0.08,rounding_size=0.14',
                        facecolor='#f8fafc', edgecolor=BORDER, linewidth=1.25)
    ax2.add_patch(b1)
    ax2.text(0.55, 8.78, '行优先 float32（SIFT1M 单份表示 488.3 MiB）', ha='left', va='center', fontsize=9.2, fontweight='bold', color=SLATE)
    for r in range(2):
        y0 = 8.20 - r * 0.42
        ax2.text(0.55, y0 + 0.15, f'x[{r}]', ha='left', va='center', fontsize=8.4, color=SLATE)
        for c in range(6):
            rect = FancyBboxPatch((1.35 + c * 1.32, y0), 1.22, 0.30, boxstyle='square,pad=0',
                                  facecolor='#e2e8f0' if r == 0 else '#cbd5e1', edgecolor='#64748b', linewidth=0.65)
            ax2.add_patch(rect)
            lbl = f'd{c}(4B)' if c < 5 else '..d127'
            ax2.text(1.35 + c * 1.32 + 0.61, y0 + 0.15, lbl, ha='center', va='center', fontsize=7.8, color='#0f172a')

    ax2.annotate('', xy=(5.0, 6.95), xytext=(5.0, 7.60), arrowprops=dict(arrowstyle='->', color=NAVY, lw=1.6))
    ax2.text(5.22, 7.28, '整数校验 [0,255] + 8 路重排（表示降 4×）', ha='left', va='center', fontsize=8.6, color=NAVY, fontweight='bold')

    b2 = FancyBboxPatch((0.25, 5.25), 9.5, 1.65, boxstyle='round,pad=0.08,rounding_size=0.14',
                        facecolor='#fffbeb', edgecolor=AMBER, linewidth=1.45)
    ax2.add_patch(b2)
    ax2.text(0.55, 6.58, '8 路 AoSoA uint8 块（字节表示 122.1 MiB，64B 对齐）', ha='left', va='center', fontsize=9.2, fontweight='bold', color='#92400e')
    colors_8 = ['#dbeafe', '#bfdbfe', '#93c5fd', '#60a5fa', '#ccfbf1', '#99f6e4', '#5eead4', '#2dd4bf']
    ax2.text(0.55, 5.92, '相邻两维:', ha='left', va='center', fontsize=8.4, color='#78350f')
    for lane in range(8):
        x0 = 2.25 + lane * 0.90
        rect = FancyBboxPatch((x0, 5.42), 0.82, 0.88, boxstyle='round,pad=0.02,rounding_size=0.06',
                              facecolor=colors_8[lane], edgecolor='#0f766e', linewidth=0.75)
        ax2.add_patch(rect)
        ax2.text(x0 + 0.41, 6.02, f'候{lane}', ha='center', va='center', fontsize=8.0, fontweight='bold', color='#0f172a')
        ax2.text(x0 + 0.41, 5.66, '2B', ha='center', va='center', fontsize=7.6, color='#334155')

    ax2.annotate('', xy=(5.0, 4.55), xytext=(5.0, 5.20), arrowprops=dict(arrowstyle='->', color=TEAL, lw=1.6))
    ax2.text(5.22, 4.88, '加载 16B → 零扩展 16×int16 (YMM 256-bit)', ha='left', va='center', fontsize=8.6, color=TEAL, fontweight='bold')

    b3 = FancyBboxPatch((0.25, 2.55), 9.5, 1.95, boxstyle='round,pad=0.08,rounding_size=0.14',
                        facecolor='#f0fdfa', edgecolor=TEAL, linewidth=1.5)
    ax2.add_patch(b3)
    ax2.text(0.55, 4.18, 'AVX2 多查询复用（参考块复用 1/2/4/8 条查询）', ha='left', va='center', fontsize=9.2, fontweight='bold', color='#115e59')
    ax2.text(0.55, 3.62, '1. Δ = vpsubw(cand_i16, q_bcast_i16)  ∈ [-255, 255]', ha='left', va='center', fontsize=8.6, color='#0f172a')
    ax2.text(0.55, 3.16, '2. acc_i32 += vpmaddwd(Δ, Δ)  (两维平方和 ≤ 130,050)', ha='left', va='center', fontsize=8.6, color='#0f172a')
    ax2.text(0.55, 2.72, '3. D ≤ 258 → ∑Δ² ≤ 16,776,450 < 2²⁴ (float32 精确)', ha='left', va='center', fontsize=8.5, color='#0f766e', fontweight='bold')

    ax2.annotate('', xy=(5.0, 1.85), xytext=(5.0, 2.50), arrowprops=dict(arrowstyle='->', color=RED, lw=1.6))
    ax2.text(5.22, 2.18, 'SIMD 阈值掩码过滤 (movemask_ps)', ha='left', va='center', fontsize=8.6, color=RED, fontweight='bold')

    b4 = FancyBboxPatch((0.25, 0.50), 9.5, 1.30, boxstyle='round,pad=0.08,rounding_size=0.14',
                        facecolor='#fef2f2', edgecolor=RED, linewidth=1.45)
    ax2.add_patch(b4)
    ax2.text(0.55, 1.46, '流式定长最大堆 Top-K 维护（容量 K）', ha='left', va='center', fontsize=9.2, fontweight='bold', color='#991b1b')
    ax2.text(0.55, 0.90, '仅掩码非零候选触发标量更新；替换后单次下沉，\n并列距离按 ID 升序确定唯一全序。', ha='left', va='center', fontsize=8.6, color='#1e293b', linespacing=1.35)

    plt.tight_layout(w_pad=1.2)
    out = out_dir / 'fig1_cross_layer_arch.png'
    fig.savefig(out)
    plt.close(fig)
    return out


# ---------------------------------------------------------------------------
# Figure 2: Phase breakdown (workload_stat.json) + Ablation ladder (internal_summary.csv)
# ---------------------------------------------------------------------------
def make_fig2(reader: BundleReader, out_dir: Path):
    ws = reader.read_json('baseline/results/perf_20261109T090707225322Z/workload_stat.json')
    rows = list(csv.DictReader(io.StringIO(ws['stdout'])))
    by_var = {}
    for r in rows:
        v = int(r['variant'])
        by_var.setdefault(v, {'a': [], 'd': [], 's': []})
        by_var[v]['a'].append(float(r['allocation_ms']))
        by_var[v]['d'].append(float(r['distance_ms']))
        by_var[v]['s'].append(float(r['selection_ms']))

    order = [0, 1, 5, 7]
    dist = np.array([statistics.median(by_var[v]['d']) for v in order])
    sel = np.array([statistics.median(by_var[v]['s']) for v in order])
    alloc = np.array([statistics.median(by_var[v]['a']) for v in order])
    totals = dist + sel + alloc  # sum of per-phase medians

    int_rows = {int(r['variant']): float(r['median_ms']) for r in reader.read_csv('baseline/results/goal_ablation_20261124T054947270218Z/internal_summary.csv')}
    base_ms = int_rows[0]
    ablation = [
        ('完整排序 + 标量距离', int_rows[0], '#64748b'),
        ('部分选择', int_rows[1], AMBER),
        ('部分选择 + 候选分块', int_rows[3], '#f59e0b'),
        ('流式最大堆 + 标量', int_rows[8], '#ea580c'),
        ('部分选择 + AVX2', int_rows[5], BLUE),
        ('部分选择 + 分块 + AVX2', int_rows[7], '#1d4ed8'),
        ('流式堆 + AVX2', int_rows[12], '#0284c7'),
        ('流式堆 + 分块 + AVX2', int_rows[14], TEAL),
    ]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.0, 4.9), gridspec_kw={'width_ratios': [1.0, 1.15]})

    labels_l = ['基础版\n全排序+标量', '算法优化\n部分选择', '+指令优化\nAVX2', '+缓存优化\n分块+AVX2']
    x = np.arange(len(order))
    w = 0.52
    ax1.bar(x, dist, w, label='距离计算', color=BLUE, edgecolor='white', linewidth=0.8)
    ax1.bar(x, sel, w, bottom=dist, label='Top-K 筛选', color=AMBER, edgecolor='white', linewidth=0.8)
    ax1.bar(x, alloc, w, bottom=dist + sel, label='内存分配', color='#94a3b8', edgecolor='white', linewidth=0.8)

    for i, tot in enumerate(totals):
        ax1.text(i, tot + 1.6, f'{tot:.1f} ms', ha='center', va='bottom', fontsize=9.4, fontweight='bold', color=NAVY)
        dp = dist[i] / tot * 100
        sp = sel[i] / tot * 100
        if dist[i] > 6.5:
            ax1.text(i, dist[i] / 2, f'{dp:.0f}%', ha='center', va='center', fontsize=9.2, color='white', fontweight='bold')
        if sel[i] > 8:
            ax1.text(i, dist[i] + sel[i] / 2, f'{sp:.0f}%', ha='center', va='center', fontsize=9.2, color='white', fontweight='bold')
        else:
            ax1.text(i, dist[i] + sel[i] / 2, f'{sp:.0f}%', ha='center', va='center', fontsize=8.4, color='#1e293b', fontweight='bold')

    ax1.annotate('筛选降 9.2×\n距离占 84.9%',
                 xy=(1.26, 25.0), xytext=(2.18, 52.0),
                 ha='center', va='center', fontsize=9.4, fontweight='bold', color=RED,
                 bbox=dict(boxstyle='round,pad=0.35', facecolor='#fef2f2', edgecolor=RED, lw=1.1),
                 arrowprops=dict(arrowstyle='->', color=RED, lw=1.4, connectionstyle='arc3,rad=-0.18'))

    ax1.set_xticks(x)
    ax1.set_xticklabels(labels_l, fontsize=9.2)
    ax1.set_ylabel('分阶段中位数之和 (ms)', fontsize=10.0, fontweight='bold', color=NAVY)
    ax1.set_ylim(0, 84)
    ax1.set_title('(a) 阶段耗时剖析与瓶颈转移\n(SIFTsmall, Q=100, K=10)', fontsize=10.8, fontweight='bold', color=NAVY, pad=10)
    ax1.legend(loc='upper right', frameon=True, facecolor='white', edgecolor='#cbd5e1', fontsize=8.8)
    ax1.grid(axis='y', alpha=0.6)
    ax1.set_axisbelow(True)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    y_pos = np.arange(len(ablation))[::-1]
    times = [r[1] for r in ablation]
    speedups = [base_ms / t for t in times]
    cols = [r[2] for r in ablation]
    names = [r[0] for r in ablation]

    ax2.barh(y_pos, times, height=0.62, color=cols, edgecolor='white', linewidth=0.8)
    for yp, t, sp in zip(y_pos, times, speedups):
        ax2.text(t + 0.45, yp, f'{t:.3f} ms ({sp:.2f}×)', ha='left', va='center', fontsize=9.1,
                 fontweight='bold' if sp in (1.0, max(speedups)) else 'normal',
                 color=TEAL if sp == max(speedups) else '#1e293b')

    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(names, fontsize=9.2)
    ax2.set_xlabel('中位耗时 (ms，越短越好)', fontsize=10.0, fontweight='bold', color=NAVY)
    ax2.set_xlim(0, 32.5)
    ax2.set_title('(b) 算法、分块与 AVX2 分层消融\n(SIFTsmall, Q=32, K=10)', fontsize=10.8, fontweight='bold', color=NAVY, pad=10)
    ax2.grid(axis='x', alpha=0.6)
    ax2.set_axisbelow(True)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    plt.tight_layout(w_pad=1.8)
    out = out_dir / 'fig2_bottleneck_ablation.png'
    fig.savefig(out)
    plt.close(fig)
    return out


# ---------------------------------------------------------------------------
# Figure 3: Server SIFT1M Path Crossover + Dual-Host Representative Speedup
# ---------------------------------------------------------------------------
def make_fig3(reader: BundleReader, out_dir: Path):
    qs = [1, 2, 4, 8, 32, 128, 256]
    srv_q10 = {}
    for q in qs:
        meds = {'adaptive': [], 'faiss_sq8_direct': [], 'faiss_blas': [], 'faiss_direct': []}
        for b in range(3):
            j = reader.read_json(f'evidence/faiss78/sift1m_q{q}_k10_b{b}.json')
            for m in meds:
                meds[m].append(j['medians'][m])
        srv_q10[q] = {m: statistics.median(v) for m, v in meds.items()}

    loc_rows = {(r['dataset'], int(r['q']), int(r['k'])): r for r in reader.read_csv('baseline/report/goal_summary.csv')}
    srv_cfg = {}
    for r in reader.read_csv('evidence/faiss78/configuration_summary.csv'):
        ds, q, k = r['dataset'], int(r['q']), int(r['k'])
        gains = [reader.read_json(f'evidence/faiss78/{ds}_q{q}_k{k}_b{b}.json')['summary']['gain'] for b in range(3)]
        srv_cfg[(ds, q, k)] = statistics.median(gains)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 4.9), gridspec_kw={'width_ratios': [1.08, 1.0]})
    x_idx = np.arange(len(qs))

    y_dir = [srv_q10[q]['faiss_direct'] / q for q in qs]
    y_sq8 = [srv_q10[q]['faiss_sq8_direct'] / q for q in qs]
    y_blas = [srv_q10[q]['faiss_blas'] / q for q in qs]
    y_custom = [srv_q10[q]['adaptive'] / q for q in qs]

    ax1.plot(x_idx, y_dir, marker='^', lw=1.9, ms=6.5, color='#94a3b8', ls=':', label='Faiss direct (float32)')
    ax1.plot(x_idx, y_sq8, marker='s', lw=2.1, ms=6.5, color=AMBER, ls='--', label='Faiss SQ8 direct (uint8)')
    ax1.plot(x_idx, y_blas, marker='D', lw=2.1, ms=6.5, color=RED, ls='-.', label='Faiss BLAS (OpenBLAS)')
    ax1.plot(x_idx, y_custom, marker='o', lw=2.7, ms=7.2, color=BLUE, label='自研自动校准版')

    ax1.set_yscale('log')
    ax1.set_xticks(x_idx)
    ax1.set_xticklabels([f'Q={q}' for q in qs], fontsize=9.4)
    ax1.set_ylabel('单条查询均摊耗时 (ms/query，对数坐标)', fontsize=9.8, fontweight='bold', color=NAVY)
    ax1.set_ylim(3.4, 290)
    ax1.set_title('(a) 学校服务器 SIFT1M (K=10) 路径切换', fontsize=10.8, fontweight='bold', color=NAVY, pad=10)

    ax1.axvspan(-0.3, 3.45, color='#eff6ff', alpha=0.55, zorder=0)
    ax1.axvspan(3.55, 6.3, color='#fefce8', alpha=0.55, zorder=0)
    ax1.text(1.5, 240, 'Q ≤ 8：最快对照\n为 SQ8 direct', ha='center', va='top', fontsize=8.8, color=NAVY,
             bbox=dict(boxstyle='round,pad=0.28', facecolor='white', edgecolor='#93c5fd', alpha=0.95))
    ax1.text(4.95, 240, 'Q ≥ 32：最快对照\n切至 BLAS', ha='center', va='top', fontsize=8.8, color='#92400e',
             bbox=dict(boxstyle='round,pad=0.28', facecolor='white', edgecolor='#fcd34d', alpha=0.95))

    ax1.annotate(f'Q=8: {y_custom[3]:.2f} ms/q (2.10×)', xy=(3, y_custom[3]), xytext=(1.75, 4.3),
                 fontsize=8.6, fontweight='bold', color=BLUE, ha='center',
                 arrowprops=dict(arrowstyle='->', color=BLUE, lw=1.1))
    ax1.annotate(f'Q=256: {y_custom[6]:.2f} vs {y_blas[6]:.2f}', xy=(6, y_custom[6]), xytext=(4.85, 4.1),
                 fontsize=8.4, color='#1e293b', ha='center',
                 arrowprops=dict(arrowstyle='->', color=SLATE, lw=1.0))

    ax1.legend(loc='upper right', bbox_to_anchor=(0.99, 0.76), frameon=True, facecolor='white', edgecolor='#cbd5e1', fontsize=8.3)
    ax1.grid(True, which='major', alpha=0.55)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    rep_cfgs = [
        ('sift1m', 1, 10, 'SIFT Q1'), ('sift1m', 2, 10, 'SIFT Q2'), ('sift1m', 4, 10, 'SIFT Q4'),
        ('sift1m', 8, 10, 'SIFT Q8'), ('sift1m', 32, 10, 'SIFT Q32'), ('sift1m', 128, 10, 'SIFT Q128'),
        ('sift1m', 256, 10, 'SIFT Q256'), ('glove25', 1, 10, 'GloVe Q1'), ('glove25', 8, 10, 'GloVe Q8'),
        ('glove25', 32, 10, 'GloVe Q32'), ('glove25', 128, 10, 'GloVe Q128'),
    ]
    loc_sp = [float(loc_rows[(d, q, k)]['faiss_median_ms']) / float(loc_rows[(d, q, k)]['custom_median_ms']) for d, q, k, _ in rep_cfgs]
    srv_sp = [srv_cfg[(d, q, k)] for d, q, k, _ in rep_cfgs]
    cfg_lbls = [lbl for _, _, _, lbl in rep_cfgs]

    x2 = np.arange(len(rep_cfgs))
    bw = 0.38
    ax2.bar(x2 - bw / 2, loc_sp, bw, label='本地 Core Ultra 9 (固定版, 均 2.09×)', color=BLUE, edgecolor='white')
    ax2.bar(x2 + bw / 2, srv_sp, bw, label='服务器 Xeon 6133 (校准版, 均 1.39×)', color=TEAL, edgecolor='white')
    ax2.axhline(1.0, color=RED, ls='--', lw=1.2, label='与最快 Faiss 持平 (1.0×)')

    for i, (ls, ss) in enumerate(zip(loc_sp, srv_sp)):
        ax2.text(i - bw / 2 - 0.03, ls + 0.08, f'{ls:.2f}', ha='center', va='bottom', fontsize=7.2, color=NAVY)
        ax2.text(i + bw / 2 + 0.03, ss + 0.08, f'{ss:.2f}', ha='center', va='bottom', fontsize=7.2, color='#115e59')

    ax2.axvline(6.5, color='#94a3b8', ls=':', lw=1.0)
    ax2.set_xticks(x2)
    ax2.set_xticklabels(cfg_lbls, rotation=32, ha='right', fontsize=8.8)
    ax2.set_ylabel('相对最快适用 Faiss 加速比 (×)', fontsize=9.8, fontweight='bold', color=NAVY)
    ax2.set_ylim(0, 5.2)
    ax2.set_title('(b) 双机代表性配置加速比对比 (K=10)', fontsize=10.8, fontweight='bold', color=NAVY, pad=10)
    ax2.legend(loc='upper right', frameon=True, facecolor='white', edgecolor='#cbd5e1', fontsize=8.3)
    ax2.grid(axis='y', alpha=0.55)
    ax2.set_axisbelow(True)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    plt.tight_layout(w_pad=1.7)
    out = out_dir / 'fig3_faiss_paths_crossover.png'
    fig.savefig(out)
    plt.close(fig)
    return out


# ---------------------------------------------------------------------------
# Figure 4: Server Auto-Calibration Impact (5 Switched Configs + All 26)
# ---------------------------------------------------------------------------
def make_fig4(reader: BundleReader, out_dir: Path):
    cfg_rows = reader.read_csv('evidence/faiss78/configuration_summary.csv')
    detail = []
    for r in cfg_rows:
        ds, q, k, mode = r['dataset'], int(r['q']), int(r['k']), int(r['mode'])
        orig_g, adapt_g, orig_m, adapt_m, sq8_m = [], [], [], [], []
        for b in range(3):
            j = reader.read_json(f'evidence/faiss78/{ds}_q{q}_k{k}_b{b}.json')
            adapt_g.append(j['summary']['gain'])
            orig_g.append(j['summary']['best_faiss_ms'] / j['summary']['original_ms'])
            orig_m.append(j['medians']['original'])
            adapt_m.append(j['medians']['adaptive'])
            if 'faiss_sq8_direct' in j['medians']:
                sq8_m.append(j['medians']['faiss_sq8_direct'])
        detail.append({
            'dataset': ds, 'q': q, 'k': k, 'mode': mode,
            'orig_ms': statistics.median(orig_m), 'adapt_ms': statistics.median(adapt_m),
            'sq8_ms': statistics.median(sq8_m) if sq8_m else None,
            'orig_gain': statistics.median(orig_g), 'adapt_gain': statistics.median(adapt_g),
            'min_gain': float(r['min_gain']), 'max_gain': float(r['max_gain']),
        })
    by_key = {(d['dataset'], d['q'], d['k']): d for d in detail}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 5.5), gridspec_kw={'width_ratios': [1.0, 1.15]})

    switched = [
        ('sift1m', 1, 1, 'SIFT Q1/K1\n(110→100)'),
        ('sift1m', 1, 10, 'SIFT Q1/K10\n(110→100)'),
        ('sift1m', 1, 100, 'SIFT Q1/K100\n(110→100)'),
        ('sift1m', 2, 10, 'SIFT Q2/K10\n(111→100)'),
        ('sift1m', 4, 10, 'SIFT Q4/K10\n(112→102)'),
    ]
    orig_ms = [by_key[(d, q, k)]['orig_ms'] for d, q, k, _ in switched]
    adapt_ms = [by_key[(d, q, k)]['adapt_ms'] for d, q, k, _ in switched]
    faiss_ms = [by_key[(d, q, k)]['sq8_ms'] for d, q, k, _ in switched]
    lbls = [l for _, _, _, l in switched]

    x = np.arange(len(switched))
    w = 0.26
    ax1.bar(x - w, orig_ms, w, label='同轮原固定分派 (mode 7)', color='#94a3b8', edgecolor='white')
    ax1.bar(x, adapt_ms, w, label='自动校准版 (改选紧凑核)', color=TEAL, edgecolor='white')
    ax1.bar(x + w, faiss_ms, w, label='最快 Faiss (SQ8 direct)', color=AMBER, edgecolor='white')

    for i in range(len(switched)):
        g = orig_ms[i] / adapt_ms[i]
        txt = f'+{(g - 1) * 100:.0f}%' if g >= 1 else f'{(g - 1) * 100:.1f}%'
        col = TEAL if g >= 1 else RED
        ax1.text(i, max(orig_ms[i], adapt_ms[i]) + 1.2, txt, ha='center', va='bottom', fontsize=9.0, fontweight='bold', color=col)

    ax1.annotate('Q=1 三项由略落后 Faiss\n转为领先 1.38–1.40×',
                 xy=(1.0, 21.0), xytext=(1.45, 44.5),
                 ha='center', va='center', fontsize=9.0, fontweight='bold', color='#0f766e',
                 bbox=dict(boxstyle='round,pad=0.35', facecolor='#f0fdfa', edgecolor=TEAL, lw=1.1),
                 arrowprops=dict(arrowstyle='->', color=TEAL, lw=1.3))

    ax1.set_xticks(x)
    ax1.set_xticklabels(lbls, fontsize=8.4)
    ax1.set_ylabel('批次中位耗时 (ms，越短越好)', fontsize=9.8, fontweight='bold', color=NAVY)
    ax1.set_ylim(0, 70)
    ax1.set_title('(a) 服务器自动校准改选 5 项对比', fontsize=10.6, fontweight='bold', color=NAVY, pad=10)
    ax1.legend(loc='upper left', frameon=True, facecolor='white', edgecolor='#cbd5e1', fontsize=8.4)
    ax1.grid(axis='y', alpha=0.55)
    ax1.set_axisbelow(True)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    all_rows = [r for r in detail if r['dataset'] == 'sift1m'] + [r for r in detail if r['dataset'] == 'glove25']
    y = np.arange(len(all_rows))[::-1]
    row_lbls = [f"{'SIFT' if r['dataset']=='sift1m' else 'GloVe'} Q{r['q']}/K{r['k']}" for r in all_rows]

    ax2.axvline(1.0, color=RED, ls='--', lw=1.2, zorder=1)
    ax2.axvspan(0.82, 1.0, color='#fef2f2', alpha=0.55, zorder=0)

    for yi, r in zip(y, all_rows):
        changed = r['mode'] != 7
        og, ag = r['orig_gain'], r['adapt_gain']
        if changed:
            ax2.plot([og, ag], [yi, yi], color=TEAL if ag > og else RED, lw=2.3, zorder=2)
            ax2.scatter([og], [yi], color='#94a3b8', s=32, zorder=3)
        ax2.plot([r['min_gain'], r['max_gain']], [yi, yi], color=BLUE if ag >= 1.0 else RED, lw=1.3, alpha=0.85, zorder=2)
        c = TEAL if (changed and ag > og) else (RED if ag < 1.0 else BLUE)
        ax2.scatter([ag], [yi], color=c, s=40, zorder=4)

    ax2.scatter([], [], color='#94a3b8', s=32, label='同轮原分派 (58/78 领先)')
    ax2.scatter([], [], color=TEAL, s=40, label='改选并提速 (Q=1/2)')
    ax2.scatter([], [], color=BLUE, s=40, label='保持领先 (≥1.0×)')
    ax2.scatter([], [], color=RED, s=40, label='大批量略慢 (<1.0×, 4项)')

    ax2.set_yticks(y)
    ax2.set_yticklabels(row_lbls, fontsize=8.0)
    ax2.set_xlabel('相对最快 Faiss 加速比 (×，虚线右侧为领先)', fontsize=9.8, fontweight='bold', color=NAVY)
    ax2.set_xlim(0.82, 2.30)
    ax2.set_title('(b) 服务器全 26 配置加速比全景 (58→67/78)', fontsize=10.6, fontweight='bold', color=NAVY, pad=10)
    ax2.legend(loc='center right', bbox_to_anchor=(0.99, 0.43), frameon=True, facecolor='white', edgecolor='#cbd5e1', fontsize=8.1)
    ax2.grid(axis='x', alpha=0.55)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    plt.tight_layout(w_pad=1.6)
    out = out_dir / 'fig4_autotune_server.png'
    fig.savefig(out)
    plt.close(fig)
    return out


# ---------------------------------------------------------------------------
# Figure 5: Automated Pipeline Flowchart + Build-Cost Amortization Curve
# ---------------------------------------------------------------------------
def make_fig5(reader: BundleReader, out_dir: Path):
    mem_rows = {(r['dataset'], r['method']): float(r['setup_ms']) for r in reader.read_csv('baseline/results/goal_memory_20261124T054856529211Z/summary.csv')}
    b_custom = mem_rows[('sift1m', 'direct_auto')]
    b_blas = mem_rows[('sift1m', 'faiss_blas')]
    b_sq8 = mem_rows[('sift1m', 'faiss_sq8_direct')]

    conf_rows = reader.read_csv('baseline/results/goal_confirmation_20261124T050444493472Z/summary.csv')
    by_cfg = {}
    for r in conf_rows:
        by_cfg.setdefault((r['dataset'], int(r['q']), int(r['k'])), {}).setdefault(r['method'], []).append(float(r['median_ms']))
    q8_c = statistics.median(by_cfg[('sift1m', 8, 10)]['direct_auto'])
    q8_sq8 = statistics.median(by_cfg[('sift1m', 8, 10)]['faiss_sq8_direct'])
    q8_blas = statistics.median(by_cfg[('sift1m', 8, 10)]['faiss_blas'])
    q128_c = statistics.median(by_cfg[('sift1m', 128, 100)]['direct_auto'])
    q128_blas = statistics.median(by_cfg[('sift1m', 128, 100)]['faiss_blas'])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 5.0), gridspec_kw={'width_ratios': [1.02, 1.0]})

    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 10)
    ax1.axis('off')
    ax1.text(5.0, 9.65, '(a) bash reproduce.sh 全自动执行流程', ha='center', va='center', fontsize=11.0, fontweight='bold', color=NAVY)

    steps = [
        (8.15, '1. 环境与硬件预检', 'Ubuntu/WSL · AVX2/FMA · 单核亲和性', '#f8fafc', SLATE),
        (6.55, '2. 编译 + 回归与 Z3 验证', '编译内核 · 边界回归 · 36+4 项 Z3 检查', '#eff6ff', BLUE),
        (4.95, '3. 原始数据解压与真值缓存', 'SIFT1M / GloVe25 / SIFTsmall 真值准备', '#f0fdfa', TEAL),
        (3.35, '4. 本机校准 / 指纹缓存复用', '首次校准 ~32.4 min ｜ 缓存复用 11.16 s', '#fffbeb', AMBER),
        (1.75, '5. 全量 78 项 Faiss 同轮对照', '随机交替 7 次取中位数（另需数十分钟）', '#fef2f2', RED),
        (0.20, '6. 自动生成报告与 SHA256 证据包', '输出 PDF/MD、raw/summary CSV 与清单', '#f1f5f9', NAVY),
    ]
    for idx, (y, title, desc, bg, edge) in enumerate(steps):
        box = FancyBboxPatch((0.25, y), 9.5, 1.15, boxstyle='round,pad=0.08,rounding_size=0.14',
                             facecolor=bg, edgecolor=edge, linewidth=1.4)
        ax1.add_patch(box)
        ax1.text(0.60, y + 0.80, title, ha='left', va='center', fontsize=9.8, fontweight='bold', color=edge)
        ax1.text(0.60, y + 0.30, desc, ha='left', va='center', fontsize=8.8, color='#1e293b')
        if idx < len(steps) - 1:
            ax1.annotate('', xy=(5.0, steps[idx + 1][0] + 1.21), xytext=(5.0, y - 0.04),
                         arrowprops=dict(arrowstyle='->', color=SLATE, lw=1.3))

    batches = np.arange(0, 26)
    cum_custom = b_custom + batches * q8_c
    cum_sq8 = b_sq8 + batches * q8_sq8
    cum_blas = b_blas + batches * q8_blas
    be_sq8 = (b_custom - b_sq8) / (q8_sq8 - q8_c)
    be_128 = (b_custom - b_blas) / (q128_blas - q128_c)

    ax2.plot(batches, cum_sq8 / 1000.0, lw=2.3, color=AMBER, ls='--', marker='s', markevery=5, ms=6.0,
             label=f'Faiss SQ8 direct ({b_sq8:.1f}ms + {q8_sq8:.1f}ms/批)')
    ax2.plot(batches, cum_blas / 1000.0, lw=2.1, color=RED, ls='-.', marker='D', markevery=5, ms=5.5,
             label=f'Faiss BLAS ({b_blas:.1f}ms + {q8_blas:.1f}ms/批)')
    ax2.plot(batches, cum_custom / 1000.0, lw=2.7, color=BLUE, marker='o', markevery=5, ms=6.5,
             label=f'自研正式版 ({b_custom:.1f}ms + {q8_c:.1f}ms/批)')

    y_be = (b_custom + be_sq8 * q8_c) / 1000.0
    ax2.scatter([be_sq8], [y_be], color=TEAL, s=80, zorder=6, edgecolor='white', linewidth=1.2)
    ax2.annotate(f'相对 SQ8 摊平:\n{math.ceil(be_sq8)} 批 ({be_sq8:.1f}批)',
                 xy=(be_sq8, y_be), xytext=(be_sq8 + 4.0, y_be - 0.27),
                 fontsize=9.2, fontweight='bold', color='#0f766e',
                 bbox=dict(boxstyle='round,pad=0.35', facecolor='#f0fdfa', edgecolor=TEAL, lw=1.1),
                 arrowprops=dict(arrowstyle='->', color=TEAL, lw=1.3))

    ax2.text(0.97, 0.05, f'Q=128/K=100 下相对 BLAS\n仅需 {math.ceil(be_128)} 批摊平建索引差值',
             transform=ax2.transAxes, ha='right', va='bottom', fontsize=8.6, color=SLATE,
             bbox=dict(boxstyle='round,pad=0.32', facecolor='#f8fafc', edgecolor='#cbd5e1'))

    ax2.set_xlabel('累计批量查询次数 (批，每批 Q=8, K=10)', fontsize=9.8, fontweight='bold', color=NAVY)
    ax2.set_ylabel('累计总耗时 = 建索引 + 查询 (秒)', fontsize=9.8, fontweight='bold', color=NAVY)
    ax2.set_xlim(0, 25)
    ax2.set_ylim(0, max(cum_blas[-1], cum_sq8[-1]) / 1000.0 * 1.14)
    ax2.set_title('(b) SIFT1M 建索引增量摊销 (本地实测)', fontsize=10.8, fontweight='bold', color=NAVY, pad=10)
    ax2.legend(loc='upper left', frameon=True, facecolor='white', edgecolor='#cbd5e1', fontsize=8.4)
    ax2.grid(True, alpha=0.55)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    plt.tight_layout(w_pad=1.6)
    out = out_dir / 'fig5_pipeline_and_amortization.png'
    fig.savefig(out)
    plt.close(fig)
    return out


def main():
    parser = argparse.ArgumentParser(description='Generate all 5 figures for the course report.')
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent.parent,
                        help='Extracted bundle root directory (default: parent of packaging/).')
    parser.add_argument('--zip', dest='zip_path', type=Path, default=None,
                        help='Optional path to submission ZIP archive instead of extracted root.')
    parser.add_argument('--out', type=Path, default=None,
                        help='Output directory for figures (default: <root>/report/figures).')
    args = parser.parse_args()

    out_dir = args.out if args.out else (args.root / 'report' / 'figures')
    out_dir.mkdir(parents=True, exist_ok=True)
    configure_style()

    reader = BundleReader(root=args.root, zip_path=args.zip_path)
    try:
        for fn in (
            lambda: make_fig1(out_dir),
            lambda: make_fig2(reader, out_dir),
            lambda: make_fig3(reader, out_dir),
            lambda: make_fig4(reader, out_dir),
            lambda: make_fig5(reader, out_dir),
        ):
            p = fn()
            print('Generated', p)
    finally:
        reader.close()


if __name__ == '__main__':
    main()
