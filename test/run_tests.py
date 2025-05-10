#!/usr/bin/env python3
import os
import sys
import yaml
import subprocess
from pathlib import Path

def normalize_value(v):
    """値を正規化して比較可能な形式に変換"""
    if isinstance(v, (int, float, bool)):
        return str(v)
    elif isinstance(v, str):
        return v.strip()
    elif isinstance(v, (list, tuple)):
        return [normalize_value(x) for x in v]
    elif isinstance(v, dict):
        return {k: normalize_value(v) for k, v in v.items()}
    return v

def deep_equal(a, b):
    """本質的な差がない場合はTrueを返す比較関数"""
    # 値を正規化
    a_norm = normalize_value(a)
    b_norm = normalize_value(b)
    
    # 辞書の場合
    if isinstance(a_norm, dict) and isinstance(b_norm, dict):
        if set(a_norm.keys()) != set(b_norm.keys()):
            return False
        return all(deep_equal(a_norm[k], b_norm[k]) for k in a_norm)
    
    # リストの場合
    elif isinstance(a_norm, list) and isinstance(b_norm, list):
        if len(a_norm) != len(b_norm):
            return False
        # リストの要素を正規化して比較
        a_sorted = sorted(str(x) for x in a_norm)
        b_sorted = sorted(str(x) for x in b_norm)
        return a_sorted == b_sorted
    
    # その他の場合
    else:
        # 文字列化して比較し、空白や改行の違いを吸収
        a_str = str(a_norm).strip().replace('\n', ' ').replace('  ', ' ')
        b_str = str(b_norm).strip().replace('\n', ' ').replace('  ', ' ')
        return a_str == b_str

def run_test(test_dir):
    print(f"\nTesting {test_dir}...")
    
    # Get the test directory name
    test_name = os.path.basename(test_dir)
    
    # Generate docker-compose.yml
    result = subprocess.run(
        [sys.executable, "main.py", f"{test_dir}/Dockerfile", f"{test_dir}/docker-compose.yml"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error generating docker-compose.yml for {test_name}:")
        print(result.stderr)
        return False
    
    # Compare with expected output
    try:
        with open(f"{test_dir}/docker-compose.yml", 'r') as f:
            generated = yaml.safe_load(f)
        
        with open(f"{test_dir}/expected_compose.yml", 'r') as f:
            expected = yaml.safe_load(f)
        
        # 本質的な差がない場合はpass
        if deep_equal(generated, expected):
            print(f"✅ {test_name} passed")
            return True
        
        # 差分を表示
        print(f"❌ {test_name} failed")
        print("Generated:")
        print(yaml.dump(generated))
        print("Expected:")
        print(yaml.dump(expected))
        
        # 差分の詳細を表示
        print("\nDifferences:")
        for key in set(generated['services'][test_name].keys()) | set(expected['services'][test_name].keys()):
            if key not in generated['services'][test_name]:
                print(f"Missing in generated: {key}")
            elif key not in expected['services'][test_name]:
                print(f"Extra in generated: {key}")
            elif generated['services'][test_name][key] != expected['services'][test_name][key]:
                print(f"Different values for {key}:")
                print(f"  Generated: {generated['services'][test_name][key]}")
                print(f"  Expected: {expected['services'][test_name][key]}")
        
        return False
            
    except Exception as e:
        print(f"Error comparing files for {test_name}: {str(e)}")
        return False

def main():
    # Get all test directories
    test_dirs = [d for d in Path("test").iterdir() if d.is_dir() and d.name.startswith("test_")]
    
    # Run tests
    results = []
    for test_dir in test_dirs:
        results.append(run_test(str(test_dir)))
    
    # Print summary
    print("\nTest Summary:")
    print(f"Total tests: {len(results)}")
    print(f"Passed: {sum(results)}")
    print(f"Failed: {len(results) - sum(results)}")
    
    # Exit with appropriate status code
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main() 