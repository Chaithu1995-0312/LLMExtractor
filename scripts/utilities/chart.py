import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# Set dark background style for crypto-native look
plt.style.use('dark_background')

# Create figure and grid layout
fig = plt.figure(figsize=(12, 8))
gs = fig.add_gridspec(2, 3, height_ratios=[2, 1], hspace=0.3)

# --- TOP PANEL: Main Observed Structure (Context) ---
ax_main = fig.add_subplot(gs[0, :])
ax_main.set_title("OBSERVED STRUCTURE: Expansion into Compression (15m)", fontsize=14, color='white', pad=20)
ax_main.set_facecolor('#0d1117')
ax_main.grid(True, linestyle='--', alpha=0.1)

# Synthetic data for the "Drop" (Expansion)
# Lower highs, lower lows, expanding range
opens_drop = [93000, 92400, 91800, 90500, 89500]
closes_drop = [92200, 91500, 90200, 89200, 88500]
highs_drop = [93100, 92600, 92000, 90800, 89800]
lows_drop = [92000, 91200, 90000, 89000, 88200]

# Synthetic data for the "Base" (Compression)
# Tight range, small bodies, overlapping
base_start_idx = len(opens_drop)
opens_base = [88500, 88600, 88450, 88550, 88500]
closes_base = [88600, 88450, 88550, 88500, 88600]
highs_base = [88700, 88700, 88600, 88650, 88700]
lows_base = [88400, 88400, 88350, 88450, 88400]

# Function to plot candles
def plot_candles(ax, start_x, opens, closes, highs, lows, color_up='green', color_down='red'):
    for i in range(len(opens)):
        x = start_x + i
        open_p = opens[i]
        close_p = closes[i]
        high_p = highs[i]
        low_p = lows[i]
        
        color = color_up if close_p >= open_p else color_down
        
        # Wick
        ax.plot([x, x], [low_p, high_p], color=color, linewidth=1)
        # Body
        rect_height = abs(close_p - open_p)
        rect_y = min(open_p, close_p)
        # Handle doji (flat body)
        if rect_height == 0: rect_height = 50 
        
        rect = patches.Rectangle((x - 0.3, rect_y), 0.6, rect_height, facecolor=color, edgecolor=color)
        ax.add_patch(rect)

# Plot Main Context
plot_candles(ax_main, 0, opens_drop, closes_drop, highs_drop, lows_drop, '#00c853', '#ff3d00')
plot_candles(ax_main, base_start_idx, opens_base, closes_base, highs_base, lows_base, '#00c853', '#ff3d00')

# Annotations for Main Graph
ax_main.annotate("EXPANSION LEG\n(Vertical > Horizontal)", xy=(1.5, 90500), xytext=(3, 91500),
                 arrowprops=dict(facecolor='white', arrowstyle='->', alpha=0.5), color='gray')
ax_main.annotate("COMPRESSION ZONE\n(Micro-Base)", xy=(6.5, 88500), xytext=(6, 89500),
                 arrowprops=dict(facecolor='white', arrowstyle='->', alpha=0.5), color='gray')

ax_main.set_xlim(-1, 10)
ax_main.set_ylim(87500, 93500)
ax_main.set_xticks([])
ax_main.set_yticks([]) # Clean look

# --- BOTTOM PANEL 1: RED STATE (Expansion) ---
ax_red = fig.add_subplot(gs[1, 0])
ax_red.set_title("🔴 RED STATE\n(Expansion / Breakdown)", fontsize=10, color='#ff3d00')
ax_red.set_facecolor('#1a0505')
ax_red.grid(False)

# Large red candles, minimal overlap
r_opens = [88400, 87800, 87000]
r_closes = [87800, 87000, 86200]
r_highs = [88450, 87900, 87100]
r_lows = [87700, 86900, 86000]
plot_candles(ax_red, 0, r_opens, r_closes, r_highs, r_lows, color_down='#ff3d00')
ax_red.set_xlim(-1, 3)
ax_red.set_ylim(85800, 88600)
ax_red.set_xticks([])
ax_red.set_yticks([])
ax_red.text(1, 85900, "Tall Bodies\nNo Overlap", ha='center', fontsize=8, color='white')

# --- BOTTOM PANEL 2: GREEN STATE (Absorption) ---
ax_green = fig.add_subplot(gs[1, 1])
ax_green.set_title("🟢 GREEN STATE\n(Absorption / Drift)", fontsize=10, color='#00c853')
ax_green.set_facecolor('#051a0a')
ax_green.grid(False)

# Small bodies, high overlap, horizontal drift
g_opens = [88500, 88550, 88520, 88580]
g_closes = [88550, 88520, 88580, 88600]
g_highs = [88600, 88600, 88650, 88650]
g_lows = [88450, 88480, 88450, 88500]
plot_candles(ax_green, 0, g_opens, g_closes, g_highs, g_lows, color_up='#00c853', color_down='#ff3d00')
ax_green.set_xlim(-1, 4)
ax_green.set_ylim(88400, 88700)
ax_green.set_xticks([])
ax_green.set_yticks([])
ax_green.text(1.5, 88420, "Cluster/Overlap\nTime > Price", ha='center', fontsize=8, color='white')

# --- BOTTOM PANEL 3: NEUTRAL STATE (Noise) ---
ax_neut = fig.add_subplot(gs[1, 2])
ax_neut.set_title("⚪ NEUTRAL STATE\n(Noise / Indecision)", fontsize=10, color='gray')
ax_neut.set_facecolor('#1c1c1c')
ax_neut.grid(False)

# Long wicks, alternating colors, no progress
n_opens = [88500, 88800, 88400]
n_closes = [88800, 88400, 88700]
n_highs = [89000, 89000, 88900]
n_lows = [88300, 88200, 88200]
plot_candles(ax_neut, 0, n_opens, n_closes, n_highs, n_lows, color_up='gray', color_down='gray')
ax_neut.set_xlim(-1, 3)
ax_neut.set_ylim(88000, 89200)
ax_neut.set_xticks([])
ax_neut.set_yticks([])
ax_neut.text(1, 88100, "Long Wicks\nInvalidation", ha='center', fontsize=8, color='white')

plt.tight_layout()
plt.show()