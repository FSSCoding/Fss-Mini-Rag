#!/usr/bin/env python3
"""
Phase 1: Container-based testing for FSS-Mini-RAG distribution.
Tests installation methods in clean Docker environments.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Test configurations for different environments
TEST_ENVIRONMENTS = [
    {
        "name": "Ubuntu 22.04",
        "image": "ubuntu:22.04",
        "setup_commands": [
            "apt-get update",
            "apt-get install -y python3 python3-pip python3-venv curl wget git",
            "python3 --version"
        ],
        "test_priority": "high"
    },
    {
        "name": "Ubuntu 20.04", 
        "image": "ubuntu:20.04",
        "setup_commands": [
            "apt-get update",
            "apt-get install -y python3 python3-pip python3-venv curl wget git",
            "python3 --version"
        ],
        "test_priority": "medium"
    },
    {
        "name": "Alpine Linux",
        "image": "alpine:latest",
        "setup_commands": [
            "apk add --no-cache python3 py3-pip bash curl wget git",
            "python3 --version"
        ],
        "test_priority": "high"
    },
    {
        "name": "CentOS Stream 9",
        "image": "quay.io/centos/centos:stream9",
        "setup_commands": [
            "dnf update -y",
            "dnf install -y python3 python3-pip curl wget git",
            "python3 --version"
        ],
        "test_priority": "medium"
    }
]

class ContainerTester:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.results = {}
        
    def check_docker(self):
        """Check if Docker is available."""
        print("🐳 Checking Docker availability...")
        
        try:
            result = subprocess.run(
                ["docker", "version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode == 0:
                print("   ✅ Docker is available")
                return True
            else:
                print(f"   ❌ Docker check failed: {result.stderr}")
                return False
        except FileNotFoundError:
            print("   ❌ Docker not installed")
            return False
        except subprocess.TimeoutExpired:
            print("   ❌ Docker check timed out")
            return False
        except Exception as e:
            print(f"   ❌ Docker check error: {e}")
            return False
    
    def pull_image(self, image):
        """Pull Docker image if not available locally."""
        print(f"📦 Pulling image {image}...")
        
        try:
            result = subprocess.run(
                ["docker", "pull", image],
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode == 0:
                print(f"   ✅ Image {image} ready")
                return True
            else:
                print(f"   ❌ Failed to pull {image}: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print(f"   ❌ Image pull timed out: {image}")
            return False
        except Exception as e:
            print(f"   ❌ Error pulling {image}: {e}")
            return False
    
    def run_container_test(self, env_config):
        """Run tests in a specific container environment."""
        name = env_config["name"]
        image = env_config["image"]
        setup_commands = env_config["setup_commands"]
        
        print(f"\n{'='*60}")
        print(f"🧪 Testing {name} ({image})")
        print(f"{'='*60}")
        
        # Pull image
        if not self.pull_image(image):
            return False, f"Failed to pull image {image}"
        
        container_name = f"fss-rag-test-{name.lower().replace(' ', '-')}"
        
        try:
            # Remove existing container if it exists
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                capture_output=True
            )
            
            # Create and start container
            docker_cmd = [
                "docker", "run", "-d",
                "--name", container_name,
                "-v", f"{self.project_root}:/work",
                "-w", "/work",
                image,
                "sleep", "3600"
            ]
            
            result = subprocess.run(docker_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return False, f"Failed to start container: {result.stderr}"
            
            print(f"   🚀 Container {container_name} started")
            
            # Run setup commands
            for cmd in setup_commands:
                print(f"   🔧 Running: {cmd}")
                exec_result = subprocess.run([
                    "docker", "exec", container_name,
                    "sh", "-c", cmd
                ], capture_output=True, text=True, timeout=120)
                
                if exec_result.returncode != 0:
                    print(f"   ❌ Setup failed: {cmd}")
                    print(f"      Error: {exec_result.stderr}")
                    return False, f"Setup command failed: {cmd}"
                else:
                    output = exec_result.stdout.strip()
                    if output:
                        print(f"      {output}")
            
            # Test install script
            install_test_result = self.test_install_script(container_name, name)
            
            # Test manual installation methods
            manual_test_result = self.test_manual_installs(container_name, name)
            
            # Cleanup container
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
            
            # Combine results
            success = install_test_result[0] and manual_test_result[0]
            details = {
                "install_script": install_test_result,
                "manual_installs": manual_test_result
            }
            
            return success, details
            
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
            return False, "Container test timed out"
        except Exception as e:
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
            return False, f"Container test error: {e}"
    
    def test_install_script(self, container_name, env_name):
        """Test the install.sh script in container."""
        print(f"\n   📋 Testing install.sh script...")
        
        try:
            # Test install script
            cmd = 'bash /work/install.sh'
            result = subprocess.run([
                "docker", "exec", container_name,
                "sh", "-c", cmd
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print("   ✅ install.sh completed successfully")
                
                # Test that rag-mini command is available
                test_cmd = subprocess.run([
                    "docker", "exec", container_name,
                    "sh", "-c", "rag-mini --help"
                ], capture_output=True, text=True, timeout=30)
                
                if test_cmd.returncode == 0:
                    print("   ✅ rag-mini command works")
                    
                    # Test basic functionality
                    func_test = subprocess.run([
                        "docker", "exec", container_name,
                        "sh", "-c", 'mkdir -p /tmp/test && echo "def hello(): pass" > /tmp/test/code.py && rag-mini init -p /tmp/test'
                    ], capture_output=True, text=True, timeout=60)
                    
                    if func_test.returncode == 0:
                        print("   ✅ Basic functionality works")
                        return True, "All install script tests passed"
                    else:
                        print(f"   ❌ Basic functionality failed: {func_test.stderr}")
                        return False, f"Functionality test failed: {func_test.stderr}"
                else:
                    print(f"   ❌ rag-mini command failed: {test_cmd.stderr}")
                    return False, f"Command test failed: {test_cmd.stderr}"
            else:
                print(f"   ❌ install.sh failed: {result.stderr}")
                return False, f"Install script failed: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            print("   ❌ Install script test timed out")
            return False, "Install script test timeout"
        except Exception as e:
            print(f"   ❌ Install script test error: {e}")
            return False, f"Install script test error: {e}"
    
    def test_manual_installs(self, container_name, env_name):
        """Test manual installation methods."""
        print(f"\n   📋 Testing manual installation methods...")
        
        # For now, we'll test pip install of the built wheel if it exists
        dist_dir = self.project_root / "dist"
        wheel_files = list(dist_dir.glob("*.whl"))
        
        if not wheel_files:
            print("   ⚠️  No wheel files found, skipping manual install tests")
            return True, "No wheels available for testing"
        
        wheel_file = wheel_files[0]
        
        try:
            # Test pip install of wheel
            cmd = f'pip3 install /work/dist/{wheel_file.name} && rag-mini --help'
            result = subprocess.run([
                "docker", "exec", container_name,
                "sh", "-c", cmd
            ], capture_output=True, text=True, timeout=180)
            
            if result.returncode == 0:
                print("   ✅ Wheel installation works")
                return True, "Manual wheel install successful"
            else:
                print(f"   ❌ Wheel installation failed: {result.stderr}")
                return False, f"Wheel install failed: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            print("   ❌ Manual install test timed out")
            return False, "Manual install timeout"
        except Exception as e:
            print(f"   ❌ Manual install test error: {e}")
            return False, f"Manual install error: {e}"
    
    def run_all_tests(self):
        """Run tests in all configured environments."""
        print("🧪 FSS-Mini-RAG Phase 1: Container Testing")
        print("=" * 60)
        
        if not self.check_docker():
            print("\n❌ Docker is required for container testing")
            print("Install Docker and try again:")
            print("   https://docs.docker.com/get-docker/")
            return False
        
        # Test high priority environments first
        high_priority = [env for env in TEST_ENVIRONMENTS if env["test_priority"] == "high"]
        medium_priority = [env for env in TEST_ENVIRONMENTS if env["test_priority"] == "medium"]
        
        all_envs = high_priority + medium_priority
        passed = 0
        total = len(all_envs)
        
        for env_config in all_envs:
            success, details = self.run_container_test(env_config)
            self.results[env_config["name"]] = {
                "success": success,
                "details": details
            }
            
            if success:
                passed += 1
                print(f"   🎉 {env_config['name']}: PASSED")
            else:
                print(f"   💥 {env_config['name']}: FAILED")
                print(f"      Reason: {details}")
        
        # Summary
        print(f"\n{'='*60}")
        print(f"📊 Phase 1 Results: {passed}/{total} environments passed")
        print(f"{'='*60}")
        
        for env_name, result in self.results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{status:>8} {env_name}")
        
        if passed == total:
            print(f"\n🎉 Phase 1: All container tests PASSED!")
            print(f"✅ Install scripts work across Linux distributions")
            print(f"✅ Basic functionality works after installation")
            print(f"\n🚀 Ready for Phase 2: Cross-Platform Testing")
        elif passed >= len(high_priority):
            print(f"\n⚠️  Phase 1: High priority tests passed ({len(high_priority)}/{len(high_priority)})")
            print(f"💡 Can proceed with Phase 2, fix failing environments later")
        else:
            print(f"\n❌ Phase 1: Critical environments failed")
            print(f"🔧 Fix install scripts before proceeding to Phase 2")
        
        # Save detailed results
        results_file = self.project_root / "test_results_phase1.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        return passed >= len(high_priority)

def main():
    """Run Phase 1 container testing."""
    project_root = Path(__file__).parent.parent
    
    tester = ContainerTester(project_root)
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())