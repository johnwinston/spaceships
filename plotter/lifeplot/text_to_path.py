"""Convert SVG text elements to paths using Inkscape command-line tool.

This module provides utilities to convert text elements in SVG files
to vector paths, making them plotter-ready.
"""

import subprocess
import tempfile
from pathlib import Path


class TextToPathConverter:
    """Converts SVG text elements to paths using Inkscape."""
    
    # Common Inkscape installation paths
    INKSCAPE_PATHS = [
        "/Applications/Inkscape.app/Contents/MacOS/inkscape",  # macOS app
        "/usr/local/bin/inkscape",  # Homebrew/MacPorts
        "/usr/bin/inkscape",  # Linux
        "inkscape",  # In PATH
    ]
    
    @classmethod
    def find_inkscape(cls) -> str:
        """Find Inkscape executable.
        
        Returns:
            Path to Inkscape executable
            
        Raises:
            FileNotFoundError: If Inkscape is not found
        """
        for path in cls.INKSCAPE_PATHS:
            try:
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        raise FileNotFoundError(
            "Inkscape not found. Please install Inkscape or add it to PATH.\n"
            "Download from: https://inkscape.org/release/"
        )
    
    @classmethod
    def convert_file(cls, input_file: Path, output_file: Path = None) -> bool:
        """Convert text to paths in an SVG file.
        
        Args:
            input_file: Input SVG file path
            output_file: Output SVG file path (defaults to overwriting input)
            
        Returns:
            True if successful, False otherwise
        """
        if output_file is None:
            output_file = input_file
        
        try:
            inkscape_path = cls.find_inkscape()
        except FileNotFoundError as e:
            print(f"Error: {e}")
            return False
        
        try:
            # Use Inkscape command-line to convert text to paths
            # --export-text-to-path converts all text elements
            result = subprocess.run(
                [
                    inkscape_path,
                    str(input_file),
                    "--export-text-to-path",
                    "--export-plain-svg",
                    f"--export-filename={output_file}"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"Inkscape error: {result.stderr}")
                return False
            
            return True
            
        except subprocess.TimeoutExpired:
            print("Error: Inkscape command timed out")
            return False
        except Exception as e:
            print(f"Error running Inkscape: {e}")
            return False
    
    @classmethod
    def convert_file_inplace(cls, svg_file: Path) -> bool:
        """Convert text to paths in-place in an SVG file.
        
        Creates a backup with .bak extension before converting.
        
        Args:
            svg_file: SVG file path to convert
            
        Returns:
            True if successful, False otherwise
        """
        # Create backup
        backup_file = svg_file.with_suffix(svg_file.suffix + '.bak')
        try:
            import shutil
            shutil.copy2(svg_file, backup_file)
        except Exception as e:
            print(f"Error creating backup: {e}")
            return False
        
        success = cls.convert_file(svg_file, svg_file)
        
        if success:
            # Remove backup on success
            try:
                backup_file.unlink()
            except:
                pass
        else:
            # Restore backup on failure
            try:
                import shutil
                shutil.copy2(backup_file, svg_file)
                backup_file.unlink()
            except:
                pass
        
        return success


def convert_text_to_paths(svg_file: Path, in_place: bool = True) -> bool:
    """Convenience function to convert text to paths in an SVG file.
    
    Args:
        svg_file: Path to SVG file
        in_place: If True, modifies file in-place (default)
                  If False, creates new file with _paths suffix
    
    Returns:
        True if successful, False otherwise
    """
    if in_place:
        return TextToPathConverter.convert_file_inplace(svg_file)
    else:
        output_file = svg_file.with_stem(svg_file.stem + '_paths')
        return TextToPathConverter.convert_file(svg_file, output_file)
