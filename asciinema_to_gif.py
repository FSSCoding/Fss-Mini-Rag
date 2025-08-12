#!/usr/bin/env python3
"""
Asciinema to GIF Converter
Converts .cast files to optimized GIF animations without external services.
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Any
import tempfile
import shutil

class AsciinemaToGIF:
    def __init__(self):
        self.temp_dir = None
        
    def check_dependencies(self) -> Dict[str, bool]:
        """Check if required tools are available."""
        tools = {
            'ffmpeg': self._check_command('ffmpeg'),
            'convert': self._check_command('convert'),  # ImageMagick
            'gifsicle': self._check_command('gifsicle')  # Optional optimizer
        }
        return tools
        
    def _check_command(self, command: str) -> bool:
        """Check if a command is available."""
        return shutil.which(command) is not None
        
    def install_instructions(self):
        """Show installation instructions for missing dependencies."""
        print("📦 Required Dependencies:")
        print()
        print("Ubuntu/Debian:")
        print("  sudo apt install ffmpeg imagemagick gifsicle")
        print()
        print("macOS:")
        print("  brew install ffmpeg imagemagick gifsicle")
        print()
        print("Arch Linux:")
        print("  sudo pacman -S ffmpeg imagemagick gifsicle")
        
    def parse_cast_file(self, cast_path: Path) -> Dict[str, Any]:
        """Parse asciinema .cast file."""
        with open(cast_path, 'r') as f:
            lines = f.readlines()
            
        # First line is header
        header = json.loads(lines[0])
        
        # Remaining lines are events
        events = []
        for line in lines[1:]:
            if line.strip():
                events.append(json.loads(line))
                
        return {
            'header': header,
            'events': events,
            'width': header.get('width', 80),
            'height': header.get('height', 24)
        }
        
    def create_frames(self, cast_data: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Create individual frame images from cast data."""
        print("🎬 Creating frames...")
        
        width = cast_data['width']
        height = cast_data['height']
        events = cast_data['events']
        
        # Terminal state
        screen = [[' ' for _ in range(width)] for _ in range(height)]
        cursor_x, cursor_y = 0, 0
        
        frames = []
        frame_count = 0
        last_time = 0
        
        for event in events:
            timestamp, event_type, data = event
            
            # Calculate delay
            delay = timestamp - last_time
            last_time = timestamp
            
            if event_type == 'o':  # Output event
                # Process terminal output
                for char in data:
                    if char == '\n':
                        cursor_y += 1
                        cursor_x = 0
                        if cursor_y >= height:
                            # Scroll up
                            screen = screen[1:] + [[' ' for _ in range(width)]]
                            cursor_y = height - 1
                    elif char == '\r':
                        cursor_x = 0
                    elif char == '\033':
                        # Skip ANSI escape sequences (simplified)
                        continue
                    elif char.isprintable():
                        if cursor_x < width and cursor_y < height:
                            screen[cursor_y][cursor_x] = char
                            cursor_x += 1
                            
                # Create frame if significant delay or content change
                if delay > 0.1 or frame_count == 0:
                    frame_path = self._create_frame_image(screen, output_dir, frame_count, delay)
                    frames.append((frame_path, delay))
                    frame_count += 1
                    
        return frames
        
    def _create_frame_image(self, screen: List[List[str]], output_dir: Path, 
                          frame_num: int, delay: float) -> Path:
        """Create a single frame image using ImageMagick."""
        # Convert screen to text
        text_content = []
        for row in screen:
            line = ''.join(row).rstrip()
            text_content.append(line)
            
        # Create text file
        text_file = output_dir / f"frame_{frame_num:04d}.txt"
        with open(text_file, 'w') as f:
            f.write('\n'.join(text_content))
            
        # Convert to image using ImageMagick
        image_file = output_dir / f"frame_{frame_num:04d}.png"
        
        cmd = [
            'convert',
            '-font', 'Liberation-Mono',  # Monospace font
            '-pointsize', '12',
            '-background', '#1e1e1e',    # Dark background
            '-fill', '#d4d4d4',          # Light text
            '-gravity', 'NorthWest',
            f'label:@{text_file}',
            str(image_file)
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return image_file
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create frame {frame_num}: {e}")
            return None
            
    def create_gif(self, frames: List[tuple], output_path: Path, fps: int = 10) -> bool:
        """Create GIF from frame images using ffmpeg."""
        print("🎞️  Creating GIF...")
        
        if not frames:
            print("❌ No frames to process")
            return False
            
        # Create ffmpeg input file list
        input_list = self.temp_dir / "input_list.txt"
        with open(input_list, 'w') as f:
            for frame_path, delay in frames:
                if frame_path and frame_path.exists():
                    duration = max(delay, 0.1)  # Minimum 0.1s per frame
                    f.write(f"file '{frame_path}'\n")
                    f.write(f"duration {duration}\n")
                    
        # Create GIF with ffmpeg
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(input_list),
            '-vf', 'fps=10,scale=800:-1:flags=lanczos,palettegen=reserve_transparent=0',
            '-y',
            str(output_path)
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ FFmpeg failed: {e}")
            return False
            
    def optimize_gif(self, gif_path: Path) -> bool:
        """Optimize GIF using gifsicle."""
        if not self._check_command('gifsicle'):
            return True  # Skip if not available
            
        print("🗜️  Optimizing GIF...")
        
        optimized_path = gif_path.with_suffix('.optimized.gif')
        
        cmd = [
            'gifsicle',
            '-O3',
            '--lossy=80',
            '--colors', '256',
            str(gif_path),
            '-o', str(optimized_path)
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            # Replace original with optimized
            shutil.move(optimized_path, gif_path)
            return True
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Optimization failed: {e}")
            return False
            
    def convert(self, cast_path: Path, output_path: Path, fps: int = 10) -> bool:
        """Convert asciinema cast file to GIF."""
        print(f"🎯 Converting {cast_path.name} to GIF...")
        
        # Check dependencies
        deps = self.check_dependencies()
        missing = [tool for tool, available in deps.items() if not available and tool != 'gifsicle']
        
        if missing:
            print(f"❌ Missing required tools: {', '.join(missing)}")
            print()
            self.install_instructions()
            return False
            
        # Create temporary directory
        self.temp_dir = Path(tempfile.mkdtemp(prefix='asciinema_gif_'))
        
        try:
            # Parse cast file
            print("📖 Parsing cast file...")
            cast_data = self.parse_cast_file(cast_path)
            
            # Create frames
            frames = self.create_frames(cast_data, self.temp_dir)
            
            if not frames:
                print("❌ No frames created")
                return False
                
            # Create GIF
            success = self.create_gif(frames, output_path, fps)
            
            if success:
                # Optimize
                self.optimize_gif(output_path)
                
                # Show results
                size_mb = output_path.stat().st_size / (1024 * 1024)
                print(f"✅ GIF created: {output_path}")
                print(f"📏 Size: {size_mb:.2f} MB")
                return True
            else:
                return False
                
        finally:
            # Cleanup
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)

def main():
    parser = argparse.ArgumentParser(description='Convert asciinema recordings to GIF')
    parser.add_argument('input', type=Path, help='Input .cast file')
    parser.add_argument('-o', '--output', type=Path, help='Output .gif file (default: same name as input)')
    parser.add_argument('--fps', type=int, default=10, help='Frames per second (default: 10)')
    
    args = parser.parse_args()
    
    if not args.input.exists():
        print(f"❌ Input file not found: {args.input}")
        sys.exit(1)
        
    if not args.output:
        args.output = args.input.with_suffix('.gif')
        
    converter = AsciinemaToGIF()
    success = converter.convert(args.input, args.output, args.fps)
    
    if success:
        print("🎉 Conversion complete!")
    else:
        print("💥 Conversion failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()