#!/usr/bin/env python3
"""
FSS-Mini-RAG Auto-Update System

Provides seamless GitHub-based updates with user-friendly interface.
Checks for new releases, downloads updates, and handles installation safely.
"""

import os
import sys
import json
import time
import shutil
import zipfile
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from .config import ConfigManager

@dataclass
class UpdateInfo:
    """Information about an available update."""
    version: str
    release_url: str
    download_url: str
    release_notes: str
    published_at: str
    is_newer: bool

class UpdateChecker:
    """
    Handles checking for and applying updates from GitHub releases.
    
    Features:
    - Checks GitHub API for latest releases
    - Downloads and applies updates safely with backup
    - Respects user preferences and rate limiting
    - Provides graceful fallbacks if network unavailable
    """
    
    def __init__(self, 
                 repo_owner: str = "FSSCoding",
                 repo_name: str = "Fss-Mini-Rag",
                 current_version: str = "2.1.0"):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.current_version = current_version
        self.github_api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self.check_frequency_hours = 24  # Check once per day
        
        # Paths
        self.app_root = Path(__file__).parent.parent
        self.cache_file = self.app_root / ".update_cache.json"
        self.backup_dir = self.app_root / ".backup"
        
        # User preferences (graceful fallback if config unavailable)
        try:
            self.config = ConfigManager(self.app_root)
        except Exception:
            self.config = None
        
    def should_check_for_updates(self) -> bool:
        """
        Determine if we should check for updates now.
        
        Respects:
        - User preference to disable updates
        - Rate limiting (once per day by default)
        - Network availability
        """
        if not REQUESTS_AVAILABLE:
            return False
            
        # Check user preference
        if hasattr(self.config, 'updates') and not getattr(self.config.updates, 'auto_check', True):
            return False
            
        # Check if we've checked recently
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                    last_check = datetime.fromisoformat(cache.get('last_check', '2020-01-01'))
                    if datetime.now() - last_check < timedelta(hours=self.check_frequency_hours):
                        return False
            except (json.JSONDecodeError, ValueError, KeyError):
                pass  # Ignore cache errors, will check anyway
                
        return True
    
    def check_for_updates(self) -> Optional[UpdateInfo]:
        """
        Check GitHub API for the latest release.
        
        Returns:
            UpdateInfo if an update is available, None otherwise
        """
        if not REQUESTS_AVAILABLE:
            return None
            
        try:
            # Get latest release from GitHub API
            response = requests.get(
                f"{self.github_api_url}/releases/latest",
                timeout=10,
                headers={"Accept": "application/vnd.github.v3+json"}
            )
            
            if response.status_code != 200:
                return None
                
            release_data = response.json()
            
            # Extract version info
            latest_version = release_data.get('tag_name', '').lstrip('v')
            release_notes = release_data.get('body', 'No release notes available.')
            published_at = release_data.get('published_at', '')
            release_url = release_data.get('html_url', '')
            
            # Find download URL for source code
            download_url = None
            for asset in release_data.get('assets', []):
                if asset.get('name', '').endswith('.zip'):
                    download_url = asset.get('browser_download_url')
                    break
            
            # Fallback to source code zip
            if not download_url:
                download_url = f"https://github.com/{self.repo_owner}/{self.repo_name}/archive/refs/tags/v{latest_version}.zip"
            
            # Check if this is a newer version
            is_newer = self._is_version_newer(latest_version, self.current_version)
            
            # Update cache
            self._update_cache(latest_version, is_newer)
            
            if is_newer:
                return UpdateInfo(
                    version=latest_version,
                    release_url=release_url,
                    download_url=download_url,
                    release_notes=release_notes,
                    published_at=published_at,
                    is_newer=True
                )
                
        except Exception as e:
            # Silently fail for network issues - don't interrupt user experience
            pass
            
        return None
    
    def _is_version_newer(self, latest: str, current: str) -> bool:
        """
        Compare version strings to determine if latest is newer.
        
        Simple semantic version comparison supporting:
        - Major.Minor.Patch (e.g., 2.1.0)
        - Major.Minor (e.g., 2.1)
        """
        def version_tuple(v):
            return tuple(map(int, (v.split("."))))
        
        try:
            return version_tuple(latest) > version_tuple(current)
        except (ValueError, AttributeError):
            # If version parsing fails, assume it's newer to be safe
            return latest != current
    
    def _update_cache(self, latest_version: str, is_newer: bool):
        """Update the cache file with check results."""
        cache_data = {
            'last_check': datetime.now().isoformat(),
            'latest_version': latest_version,
            'is_newer': is_newer
        }
        
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except Exception:
            pass  # Ignore cache write errors
    
    def download_update(self, update_info: UpdateInfo, progress_callback=None) -> Optional[Path]:
        """
        Download the update package to a temporary location.
        
        Args:
            update_info: Information about the update to download
            progress_callback: Optional callback for progress updates
            
        Returns:
            Path to downloaded file, or None if download failed
        """
        if not REQUESTS_AVAILABLE:
            return None
            
        try:
            # Create temporary file for download
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
                tmp_path = Path(tmp_file.name)
                
            # Download with progress tracking
            response = requests.get(update_info.download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(tmp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)
                            
            return tmp_path
            
        except Exception as e:
            # Clean up on error
            if 'tmp_path' in locals() and tmp_path.exists():
                tmp_path.unlink()
            return None
    
    def create_backup(self) -> bool:
        """
        Create a backup of the current installation.
        
        Returns:
            True if backup created successfully
        """
        try:
            # Remove old backup if it exists
            if self.backup_dir.exists():
                shutil.rmtree(self.backup_dir)
                
            # Create new backup
            self.backup_dir.mkdir(exist_ok=True)
            
            # Copy key files and directories
            important_items = [
                'mini_rag',
                'rag-mini.py',
                'rag-tui.py', 
                'requirements.txt',
                'install_mini_rag.sh',
                'install_windows.bat',
                'README.md',
                'assets'
            ]
            
            for item in important_items:
                src = self.app_root / item
                if src.exists():
                    if src.is_dir():
                        shutil.copytree(src, self.backup_dir / item)
                    else:
                        shutil.copy2(src, self.backup_dir / item)
                        
            return True
            
        except Exception as e:
            return False
    
    def apply_update(self, update_package_path: Path, update_info: UpdateInfo) -> bool:
        """
        Apply the downloaded update.
        
        Args:
            update_package_path: Path to the downloaded update package
            update_info: Information about the update
            
        Returns:
            True if update applied successfully
        """
        try:
            # Extract to temporary directory first
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                
                # Extract the archive
                with zipfile.ZipFile(update_package_path, 'r') as zip_ref:
                    zip_ref.extractall(tmp_path)
                
                # Find the extracted directory (may be nested)
                extracted_dirs = [d for d in tmp_path.iterdir() if d.is_dir()]
                if not extracted_dirs:
                    return False
                    
                source_dir = extracted_dirs[0]
                
                # Copy files to application directory
                important_items = [
                    'mini_rag',
                    'rag-mini.py',
                    'rag-tui.py',
                    'requirements.txt',
                    'install_mini_rag.sh', 
                    'install_windows.bat',
                    'README.md'
                ]
                
                for item in important_items:
                    src = source_dir / item
                    dst = self.app_root / item
                    
                    if src.exists():
                        if dst.exists():
                            if dst.is_dir():
                                shutil.rmtree(dst)
                            else:
                                dst.unlink()
                                
                        if src.is_dir():
                            shutil.copytree(src, dst)
                        else:
                            shutil.copy2(src, dst)
                
                # Update version info
                self._update_version_info(update_info.version)
                
                return True
                
        except Exception as e:
            return False
    
    def _update_version_info(self, new_version: str):
        """Update version information in the application."""
        # Update __init__.py version
        init_file = self.app_root / 'mini_rag' / '__init__.py'
        if init_file.exists():
            try:
                content = init_file.read_text()
                updated_content = content.replace(
                    f'__version__ = "{self.current_version}"',
                    f'__version__ = "{new_version}"'
                )
                init_file.write_text(updated_content)
            except Exception:
                pass
    
    def rollback_update(self) -> bool:
        """
        Rollback to the backup version if update failed.
        
        Returns:
            True if rollback successful
        """
        if not self.backup_dir.exists():
            return False
            
        try:
            # Restore from backup
            for item in self.backup_dir.iterdir():
                dst = self.app_root / item.name
                
                if dst.exists():
                    if dst.is_dir():
                        shutil.rmtree(dst)
                    else:
                        dst.unlink()
                        
                if item.is_dir():
                    shutil.copytree(item, dst)
                else:
                    shutil.copy2(item, dst)
                    
            return True
            
        except Exception as e:
            return False
    
    def restart_application(self):
        """Restart the application after update."""
        try:
            # Get the current script path
            current_script = sys.argv[0]
            
            # Restart with the same arguments
            if sys.platform.startswith('win'):
                # Windows
                subprocess.Popen([sys.executable] + sys.argv)
            else:
                # Unix-like systems
                os.execv(sys.executable, [sys.executable] + sys.argv)
                
        except Exception as e:
            # If restart fails, just exit gracefully
            print(f"\n✅ Update complete! Please restart the application manually.")
            sys.exit(0)


def get_legacy_notification() -> Optional[str]:
    """
    Check if this is a legacy version that needs urgent notification.
    
    For users who downloaded before the auto-update system.
    """
    try:
        # Check if this is a very old version by looking for cache file
        # Old versions won't have update cache, so we can detect them
        app_root = Path(__file__).parent.parent
        cache_file = app_root / ".update_cache.json"
        
        # Also check version in __init__.py to see if it's old
        init_file = app_root / 'mini_rag' / '__init__.py'
        if init_file.exists():
            content = init_file.read_text()
            if '__version__ = "2.0.' in content or '__version__ = "1.' in content:
                return """
🚨 IMPORTANT UPDATE AVAILABLE 🚨

Your version of FSS-Mini-RAG is missing critical updates!

🔧 Recent improvements include:
• Fixed LLM response formatting issues  
• Added context window configuration
• Improved Windows installer reliability
• Added auto-update system (this notification!)

📥 Please update by downloading the latest version:
   https://github.com/FSSCoding/Fss-Mini-Rag/releases/latest

💡 After updating, you'll get automatic update notifications!
"""
    except Exception:
        pass
        
    return None


# Global convenience functions
_updater_instance = None

def check_for_updates() -> Optional[UpdateInfo]:
    """Global function to check for updates."""
    global _updater_instance
    if _updater_instance is None:
        _updater_instance = UpdateChecker()
    
    if _updater_instance.should_check_for_updates():
        return _updater_instance.check_for_updates()
    return None

def get_updater() -> UpdateChecker:
    """Get the global updater instance."""
    global _updater_instance
    if _updater_instance is None:
        _updater_instance = UpdateChecker()
    return _updater_instance