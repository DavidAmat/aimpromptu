# Color Palette

It is defined in python but you can implement it in a `.ts` equivalent. It contains some colors by name (which it is better to call them by this alias when we refer to them) and its darkness (dark or light).
You are free to use all the spectrum of grays you want, the "Gray" Dark and Light are two standard ones I used.

```python
import seaborn as sns
import matplotlib.pyplot as plt

# Define brand palettes as nested dictionary
brand_palettes = {
    "dark": {
        "Blue": "#4681ff",
        "Pink": "#ff6495",
        "Lavender": "#816eff",
        "Yellow": "#ffc83c",
        "Green": "#3cdcb4",
        "Orange": "#ff8b32",
        "Brown": "#664E3C",
        "Red": "#FE6060",
        "Cyan": "#00E7E7",
        "Gray": "#393939",
    },
    "light": {
        "Blue": "#A2C0FF",
        "Pink": "#FFB1CA",
        "Lavender": "#C0B6FF",
        "Yellow": "#FFE39D",
        "Green": "#9DEDD9",
        "Orange": "#FFC598",
        "Brown": "#B2A69D",
        "Red": "#FEAFAF",
        "Cyan": "#B2F7F7",
        "Gray": "#9C9C9C",
    },
}

# Extract the palettes in the correct order
dark_colors = list(brand_palettes["dark"].values())
light_colors = list(brand_palettes["light"].values())

# Plot both palettes
fig, axes = plt.subplots(2, 1, figsize=(10, 2), constrained_layout=True)

# Plot DARKS
axes[0].imshow([sns.color_palette(dark_colors)], extent=[0, 10, 0, 1])
axes[0].set_title("DARKS", fontsize=12, fontweight='bold')

# Plot LIGHTS
axes[1].imshow([sns.color_palette(light_colors)], extent=[0, 10, 0, 1])
axes[1].set_title("LIGHTS", fontsize=12, fontweight='bold')

# Clean up appearance
for ax in axes:
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

plt.show()

```