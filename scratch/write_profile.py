from pathlib import Path

profile_path = Path('C:/Users/soura/Documents/WindowsPowerShell/Microsoft.PowerShell_profile.ps1')
profile_path.parent.mkdir(parents=True, exist_ok=True)

profile_code = """
function fcc-server {
    & "C:\\Users\\soura\\AppData\\Roaming\\uv\\tools\\free-claude-code\\Scripts\\python.exe" -c "import sys, os; sys.path = [p for p in sys.path if p not in ('', os.getcwd())]; from cli.entrypoints import serve; serve()" @args
}

function fcc-init {
    & "C:\\Users\\soura\\AppData\\Roaming\\uv\\tools\\free-claude-code\\Scripts\\python.exe" -c "import sys, os; sys.path = [p for p in sys.path if p not in ('', os.getcwd())]; from cli.entrypoints import init; init()" @args
}

function fcc-claude {
    & "C:\\Users\\soura\\AppData\\Roaming\\uv\\tools\\free-claude-code\\Scripts\\python.exe" -c "import sys, os; sys.path = [p for p in sys.path if p not in ('', os.getcwd())]; from cli.launchers.claude import launch; launch()" @args
}

function fcc-codex {
    & "C:\\Users\\soura\\AppData\\Roaming\\uv\\tools\\free-claude-code\\Scripts\\python.exe" -c "import sys, os; sys.path = [p for p in sys.path if p not in ('', os.getcwd())]; from cli.launchers.codex import launch; launch()" @args
}
"""

profile_path.write_text(profile_code.strip() + "\\n", encoding='utf-8')
print("PowerShell profile written successfully.")
