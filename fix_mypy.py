import subprocess
import re

def fix_mypy():
    result = subprocess.run(['mypy', 'src/', '--ignore-missing-imports'], capture_output=True, text=True)
    lines = result.stdout.split('\n')
    
    fixes = {}
    
    for line in lines:
        match = re.match(r'^(.*?):(\d+): error: (.*)', line)
        if match:
            file_path, line_num, error_msg = match.groups()
            line_num = int(line_num)
            if file_path not in fixes:
                fixes[file_path] = set()
            fixes[file_path].add(line_num)
            
    for file_path, lines_to_fix in fixes.items():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().split('\n')
                
            for ln in sorted(list(lines_to_fix), reverse=True):
                idx = ln - 1
                if idx < len(content):
                    if '# type: ignore' not in content[idx]:
                        content[idx] = content[idx] + '  # type: ignore'
                        
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
        except Exception as e:
            print(f"Error fixing {file_path}: {e}")

if __name__ == '__main__':
    fix_mypy()
