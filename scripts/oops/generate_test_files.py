#!/usr/bin/env python3
"""
Generate Test Files for Benchmarks

Creates sample PDFs and images of various sizes for benchmarking.
Usage:
    python scripts/generate_test_files.py
    python scripts/generate_test_files.py --output ./test_files --count 20
"""

import argparse
import io
from pathlib import Path

from PIL import Image


def generate_jpeg(output_path: Path, size_kb: int) -> int:
    """Generate a JPEG of approximately the target size."""
    dimension = int((size_kb * 1024 * 0.7) ** 0.5)
    dimension = max(100, min(dimension, 4000))

    img = Image.new("RGB", (dimension, dimension), color=(73, 109, 137))

    for y in range(0, dimension, 50):
        for x in range(0, dimension, 50):
            color = ((x * 3) % 256, (y * 2) % 256, ((x + y) % 256))
            for dy in range(min(50, dimension - y)):
                for dx in range(min(50, dimension - x)):
                    if 0 <= y + dy < dimension and 0 <= x + dx < dimension:
                        img.putpixel((x + dx, y + dy), color)

    buffer = io.BytesIO()
    quality = 85
    img.save(buffer, format="JPEG", quality=quality)

    while buffer.tell() < size_kb * 1024 and dimension < 4000:
        dimension = int(dimension * 1.1)
        img = img.resize((dimension, dimension))
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)

    output_path.write_bytes(buffer.getvalue())
    return len(buffer.getvalue())


def generate_png(output_path: Path, size_kb: int) -> int:
    """Generate a PNG of approximately the target size."""
    dimension = int((size_kb * 1024 * 0.3) ** 0.5)
    dimension = max(100, min(dimension, 3000))

    img = Image.new("RGBA", (dimension, dimension), color=(73, 109, 137, 255))

    for y in range(0, dimension, 100):
        for x in range(0, dimension, 100):
            color = ((x * 3) % 256, (y * 2) % 256, ((x + y) % 256), 255)
            for dy in range(min(100, dimension - y)):
                for dx in range(min(100, dimension - x)):
                    if 0 <= y + dy < dimension and 0 <= x + dx < dimension:
                        img.putpixel((x + dx, y + dy), color)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")

    output_path.write_bytes(buffer.getvalue())
    return len(buffer.getvalue())


def generate_pdf(output_path: Path, num_pages: int = 1) -> int:
    """Generate a simple PDF with the specified number of pages."""
    try:
        import pikepdf

        with pikepdf.new() as pdf:
            for _ in range(num_pages):
                pdf.add_blank_page(page_size=(612, 792))

            pdf.save(str(output_path))
        return output_path.stat().st_size

    except ImportError:
        print("Warning: pikepdf not available, creating minimal PDF")
        minimal_pdf = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
194
%%EOF"""
        output_path.write_bytes(minimal_pdf)
        return len(minimal_pdf)


def main():
    parser = argparse.ArgumentParser(description="Generate test files for benchmarks")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path(__file__).parent.parent / "tests" / "benchmarks" / "fixtures",
        help="Output directory for test files",
    )
    parser.add_argument(
        "--count",
        "-c",
        type=int,
        default=10,
        help="Number of files of each type to generate",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing files before generating",
    )

    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.clean:
        print(f"Cleaning {output_dir}...")
        for f in output_dir.glob("*"):
            if f.is_file():
                f.unlink()

    print(f"Generating test files in {output_dir}...")
    print()

    total_size = 0

    jpeg_sizes = [100, 250, 500, 1000, 2000]
    for size_kb in jpeg_sizes:
        for i in range(args.count):
            filename = f"jpeg_{size_kb}kb_{i:03d}.jpg"
            filepath = output_dir / filename
            actual_size = generate_jpeg(filepath, size_kb)
            total_size += actual_size
            print(f"  Created {filename} ({actual_size / 1024:.1f} KB)")

    png_sizes = [100, 250, 500]
    for size_kb in png_sizes:
        for i in range(args.count):
            filename = f"png_{size_kb}kb_{i:03d}.png"
            filepath = output_dir / filename
            actual_size = generate_png(filepath, size_kb)
            total_size += actual_size
            print(f"  Created {filename} ({actual_size / 1024:.1f} KB)")

    pdf_pages = [1, 3, 5, 10, 25]
    for num_pages in pdf_pages:
        for i in range(args.count):
            filename = f"pdf_{num_pages}pages_{i:03d}.pdf"
            filepath = output_dir / filename
            actual_size = generate_pdf(filepath, num_pages)
            total_size += actual_size
            print(f"  Created {filename} ({actual_size / 1024:.1f} KB)")

    print()
    print("=" * 50)
    file_count = len(list(output_dir.glob("*")))
    print(f"Generated {file_count} files")
    print(f"Total size: {total_size / (1024 * 1024):.2f} MB")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
