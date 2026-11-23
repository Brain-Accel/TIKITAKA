"""require_convention_skill.py 검사. 실행: python3 .claude/hooks/test_require_convention_skill.py"""

import json
import os
import subprocess
import sys
import tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "require_convention_skill.py")
SKILL_USE = '{"type":"tool_use","name":"Skill","input":{"skill":"%s"}}'


def run(event, project):
    result = subprocess.run(
        [sys.executable, HOOK],
        input=event if isinstance(event, str) else json.dumps(event),
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": project},
    )
    return result.returncode, result.stderr


def transcript(directory, name, *lines):
    path = os.path.join(directory, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(['{"type":"user","message":"hi"}', *lines]) + "\n")
    return path


def edit(project, relative, transcript_path, **extra):
    return {
        "tool_name": "Edit",
        "tool_input": {"file_path": os.path.join(project, relative)},
        "transcript_path": transcript_path,
        "cwd": project,
        **extra,
    }


def main():
    with tempfile.TemporaryDirectory() as root:
        project = os.path.join(root, "TIKITAKA")
        os.makedirs(project)
        empty = transcript(root, "empty.jsonl")
        with_backend = transcript(root, "backend.jsonl", SKILL_USE % "backend-architecture")
        with_rn_read = transcript(
            root, "rn.jsonl", '{"name":"Read","input":{"file_path":"/x/.claude/skills/react-native-code-standards/SKILL.md"}}'
        )

        code, err = run(edit(project, "backend/src/A.kt", empty), project)
        assert code == 2 and "backend-architecture" in err, (code, err)

        assert run(edit(project, "backend/src/A.kt", with_backend), project)[0] == 0

        code, err = run(edit(project, "app/src/A.tsx", with_backend), project)
        assert code == 2 and "react-native-code-standards" in err, (code, err)

        assert run(edit(project, "app/src/A.tsx", with_rn_read), project)[0] == 0
        mention_only = transcript(root, "mention.jsonl", '{"type":"text","text":"see .claude/skills/react-native-code-standards/SKILL.md"}')
        assert run(edit(project, "app/src/A.tsx", mention_only), project)[0] == 2
        edited_only = transcript(root, "edited.jsonl", '{"name":"Edit","input":{"file_path":"/x/.claude/skills/react-native-code-standards/SKILL.md"}}')
        assert run(edit(project, "app/src/A.tsx", edited_only), project)[0] == 2
        assert run(edit(project, "CLAUDE.md", empty), project)[0] == 0
        assert run(edit(project, "../elsewhere/backend/A.kt", empty), project)[0] == 0
        assert run(edit(project, "backend/A.kt", os.path.join(root, "missing.jsonl")), project)[0] == 0
        assert run("not json", project)[0] == 0

        notebook = {"tool_name": "NotebookEdit", "tool_input": {"notebook_path": os.path.join(project, "app/n.ipynb")},
                    "transcript_path": empty, "cwd": project}
        assert run(notebook, project)[0] == 2

        # 서브에이전트는 메인 세션이 아니라 자기 기록에서 스킬을 읽었는지 봅니다
        main_path = transcript(root, "session.jsonl", SKILL_USE % "backend-architecture")
        transcript(root, "session/subagents/agent-sub1.jsonl")
        transcript(root, "session/subagents/agent-sub2.jsonl", SKILL_USE % "backend-architecture")
        assert run(edit(project, "backend/A.kt", main_path, agent_id="sub1"), project)[0] == 2
        assert run(edit(project, "backend/A.kt", main_path, agent_id="sub2"), project)[0] == 0

    print("require_convention_skill: 13 checks passed")


if __name__ == "__main__":
    main()
