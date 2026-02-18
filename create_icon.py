"""Generate BruceLeads app icon (.ico) with multiple sizes."""
from PIL import Image, ImageDraw, ImageFont
import math, os

def create_icon(size):
    """Create a single icon image at the given size."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # --- Background: rounded rectangle with gradient-like effect ---
    margin = max(1, size // 32)
    radius = size // 5
    
    # Base purple gradient (simulated with two overlapping rounded rects)
    # Dark purple base
    draw.rounded_rectangle(
        [margin, margin, size - margin - 1, size - margin - 1],
        radius=radius, fill=(88, 28, 135)  # purple-900
    )
    # Lighter purple overlay on top portion for gradient effect
    draw.rounded_rectangle(
        [margin, margin, size - margin - 1, int(size * 0.6)],
        radius=radius, fill=(124, 58, 237)  # purple-600
    )
    # Blend middle
    for i in range(max(1, size // 8)):
        y = int(size * 0.5) + i
        alpha = int(255 * (1 - i / max(1, size // 8)))
        draw.line(
            [(margin + radius // 2, y), (size - margin - radius // 2, y)],
            fill=(124, 58, 237, alpha)
        )
    
    # --- Lightning bolt / lead icon ---
    cx, cy = size // 2, size // 2
    s = size / 256  # scale factor
    
    if size >= 32:
        # Draw a stylized "B" + lightning bolt hybrid
        # Lightning bolt points (centered, scaled)
        bolt_points = [
            (cx + int(10 * s), cy - int(50 * s)),   # top right
            (cx - int(15 * s), cy - int(5 * s)),     # middle left
            (cx + int(5 * s), cy - int(5 * s)),      # middle center-right
            (cx - int(10 * s), cy + int(50 * s)),    # bottom left
            (cx + int(15 * s), cy + int(5 * s)),     # middle right
            (cx - int(5 * s), cy + int(5 * s)),      # middle center-left
        ]
        
        # White lightning bolt
        draw.polygon(bolt_points, fill=(255, 255, 255))
        
        # Small circle accent at top-right
        accent_r = max(2, int(8 * s))
        draw.ellipse(
            [cx + int(25 * s) - accent_r, cy - int(40 * s) - accent_r,
             cx + int(25 * s) + accent_r, cy - int(40 * s) + accent_r],
            fill=(250, 204, 21)  # yellow accent
        )
        
        # Small circle accent at bottom-left  
        accent_r2 = max(1, int(5 * s))
        draw.ellipse(
            [cx - int(30 * s) - accent_r2, cy + int(35 * s) - accent_r2,
             cx - int(30 * s) + accent_r2, cy + int(35 * s) + accent_r2],
            fill=(167, 139, 250)  # purple-400 accent
        )
    else:
        # For very small sizes, just draw a simple bolt shape
        draw.polygon([
            (cx + 1, cy - 5), (cx - 2, cy), (cx + 1, cy),
            (cx - 1, cy + 5), (cx + 2, cy), (cx - 1, cy)
        ], fill=(255, 255, 255))
    
    return img


def main():
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [create_icon(s) for s in sizes]
    
    ico_path = os.path.join(os.path.dirname(__file__), "bruceLeads.ico")
    # Save as ICO with all sizes
    images[-1].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[:-1]
    )
    print(f"Icon saved: {ico_path}")
    print(f"Sizes: {sizes}")
    
    # Also save a PNG for reference
    png_path = os.path.join(os.path.dirname(__file__), "bruceLeads_icon.png")
    images[-1].save(png_path)
    print(f"PNG preview saved: {png_path}")


if __name__ == "__main__":
    main()
