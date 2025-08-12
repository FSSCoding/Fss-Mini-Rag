#!/bin/bash
# Create both demo GIFs for FSS-Mini-RAG

echo "🎬 FSS-Mini-RAG Demo GIF Creation Script"
echo "========================================"
echo

# Check dependencies
if ! command -v asciinema &> /dev/null; then
    echo "❌ asciinema not found. Install with:"
    echo "   curl -sL https://asciinema.org/install | sh"
    exit 1
fi

if ! command -v agg &> /dev/null; then
    echo "❌ agg not found. Install with:"
    echo "   cargo install --git https://github.com/asciinema/agg"
    exit 1
fi

echo "✅ Dependencies found: asciinema, agg"
echo

# Create recordings directory
mkdir -p recordings

# Demo 1: Synthesis Mode
echo "🚀 Creating Synthesis Mode Demo..."
echo "==================================="
echo "This demo shows fast RAG search with AI synthesis"
echo
read -p "Press Enter to record Synthesis Mode demo..."

echo "Recording in 3 seconds..."
sleep 1
echo "2..."
sleep 1  
echo "1..."
sleep 1

asciinema rec recordings/synthesis_demo.cast -c "python3 create_synthesis_demo.py" --overwrite

echo
echo "🎨 Converting to GIF..."
agg recordings/synthesis_demo.cast recordings/synthesis_demo.gif

echo "✅ Synthesis demo saved: recordings/synthesis_demo.gif"
echo

# Demo 2: Exploration Mode  
echo "🧠 Creating Exploration Mode Demo..."
echo "===================================="
echo "This demo shows interactive thinking mode with conversation memory"
echo
read -p "Press Enter to record Exploration Mode demo..."

echo "Recording in 3 seconds..."
sleep 1
echo "2..."
sleep 1
echo "1..."
sleep 1

asciinema rec recordings/exploration_demo.cast -c "python3 create_exploration_demo.py" --overwrite

echo
echo "🎨 Converting to GIF..."
agg recordings/exploration_demo.gif recordings/exploration_demo.gif

echo "✅ Exploration demo saved: recordings/exploration_demo.gif"
echo

# Summary
echo "🎉 DEMO CREATION COMPLETE!"
echo "=========================="
echo 
echo "📁 Created files:"
echo "   • recordings/synthesis_demo.cast"
echo "   • recordings/synthesis_demo.gif" 
echo "   • recordings/exploration_demo.cast"
echo "   • recordings/exploration_demo.gif"
echo
echo "💡 Usage suggestions:"
echo "   • Use synthesis_demo.gif to show fast RAG search capabilities"
echo "   • Use exploration_demo.gif to show interactive learning features" 
echo "   • Both demonstrate the clean two-mode architecture"
echo
echo "🚀 Upload to GitHub:"
echo "   • Replace existing demo.gif with synthesis_demo.gif for main README"  
echo "   • Add exploration_demo.gif for exploration mode documentation"
echo "   • Consider side-by-side comparison showing both modes"
echo

# Optional: create side-by-side comparison
read -p "Create side-by-side comparison image? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v ffmpeg &> /dev/null; then
        echo "🎬 Creating side-by-side comparison..."
        
        # Convert GIFs to MP4 first (better quality)
        ffmpeg -i recordings/synthesis_demo.gif -c:v libx264 -pix_fmt yuv420p recordings/synthesis_demo.mp4 -y
        ffmpeg -i recordings/exploration_demo.gif -c:v libx264 -pix_fmt yuv420p recordings/exploration_demo.mp4 -y
        
        # Create side-by-side
        ffmpeg -i recordings/synthesis_demo.mp4 -i recordings/exploration_demo.mp4 -filter_complex \
        "[0:v][1:v]hstack=inputs=2[v]" -map "[v]" recordings/side_by_side_demo.mp4 -y
        
        # Convert back to GIF
        ffmpeg -i recordings/side_by_side_demo.mp4 recordings/side_by_side_demo.gif -y
        
        echo "✅ Side-by-side demo created: recordings/side_by_side_demo.gif"
    else
        echo "⚠️  ffmpeg not found - skipping side-by-side creation"
    fi
fi

echo
echo "🎯 Next Steps:"  
echo "   1. Review the generated GIFs"
echo "   2. Update README.md with new demos"
echo "   3. Upload to GitHub for better project presentation"
echo "   4. Consider adding both GIFs to documentation"