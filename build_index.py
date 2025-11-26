# -*- coding: utf-8 -*-
"""
根据 projects 目录自动生成 ProjectLab 的项目索引，
更新 README.md 中 <!-- project_index:start --> ... <!-- project_index:end --> 之间的内容。
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECTS_DIR = ROOT / "projects"
README = ROOT / "README.md"

def build_index_text() -> str:
    items = []
    if PROJECTS_DIR.exists():
        for folder in sorted(PROJECTS_DIR.iterdir()):
            if folder.is_dir():
                readme = folder / "README.md"
                if not readme.exists():
                    continue
                lines = readme.read_text(encoding="utf-8").splitlines()
                if not lines:
                    continue
                # 取第一行标题作为显示名称
                title_line = lines[0]
                title = title_line.lstrip("#").strip()
                rel_path = readme.relative_to(ROOT).as_posix()
                items.append(f"- [{title}]({rel_path})")
    if not items:
        return "_暂时没有项目_"
    return "\n".join(items)

def main():
    text = README.read_text(encoding="utf-8")
    start = "<!-- project_index:start -->"
    end = "<!-- project_index:end -->"

    if start not in text or end not in text:
        raise RuntimeError("README.md 中缺少 project_index 标记")

    before, _, rest = text.partition(start)
    _, _, after = rest.partition(end)

    index_text = build_index_text()
    new_text = before + start + "\n" + index_text + "\n" + end + after

    README.write_text(new_text, encoding="utf-8")
    print("项目索引已更新。")

if __name__ == "__main__":
    main()
