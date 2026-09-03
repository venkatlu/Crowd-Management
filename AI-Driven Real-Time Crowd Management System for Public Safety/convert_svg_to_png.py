#!/usr/bin/env python3
"""
Convert SVG to PNG
"""
import sys
import os

def convert_svg_to_png():
    """Convert architecture_diagram.svg to PNG"""
    svg_path = "architecture_diagram.svg"
    png_path = "architecture_diagram.png"
    
    if not os.path.exists(svg_path):
        print(f"Error: {svg_path} not found!")
        return False
    
    # Try using cairosvg first (most reliable)
    try:
        import cairosvg
        print("Using cairosvg to convert SVG to PNG...")
        cairosvg.svg2png(url=svg_path, write_to=png_path, output_width=2400, output_height=1800)
        print(f"✓ Successfully converted to {png_path}")
        return True
    except ImportError:
        print("cairosvg not installed, trying alternative method...")
    except Exception as e:
        print(f"Error with cairosvg: {e}")
        print("Trying alternative method...")
    
    # Try using svglib + reportlab
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPM
        print("Using svglib to convert SVG to PNG...")
        drawing = svg2rlg(svg_path)
        if drawing:
            renderPM.drawToFile(drawing, png_path, fmt='PNG', dpi=300)
            print(f"✓ Successfully converted to {png_path}")
            return True
        else:
            print("Error: Could not parse SVG file")
    except ImportError:
        print("svglib not installed, trying Pillow method...")
    except Exception as e:
        print(f"Error with svglib: {e}")
        print("Trying Pillow method...")
    
    # Try using Pillow with wand (ImageMagick binding)
    try:
        from wand.image import Image
        print("Using Wand (ImageMagick) to convert SVG to PNG...")
        with Image(filename=svg_path) as img:
            img.format = 'png'
            img.resolution = (300, 300)
            img.save(filename=png_path)
        print(f"✓ Successfully converted to {png_path}")
        return True
    except ImportError:
        print("wand not installed")
    except Exception as e:
        print(f"Error with wand: {e}")
    
    # Last resort: Try using subprocess with system tools
    print("\nTrying system tools...")
    import subprocess
    
    # Try rsvg-convert (librsvg)
    try:
        result = subprocess.run(
            ['rsvg-convert', '-f', 'png', '-o', png_path, '-w', '2400', svg_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and os.path.exists(png_path):
            print(f"✓ Successfully converted to {png_path} using rsvg-convert")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Try inkscape
    try:
        result = subprocess.run(
            ['inkscape', '--export-type=png', f'--export-filename={png_path}', 
             f'--export-width=2400', svg_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and os.path.exists(png_path):
            print(f"✓ Successfully converted to {png_path} using Inkscape")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    print("\n❌ Could not convert SVG to PNG. Please install one of:")
    print("   - cairosvg: pip install cairosvg")
    print("   - svglib: pip install svglib reportlab")
    print("   - wand: pip install Wand (requires ImageMagick)")
    print("   - Or install system tools: rsvg-convert or inkscape")
    return False

if __name__ == "__main__":
    success = convert_svg_to_png()
    sys.exit(0 if success else 1)