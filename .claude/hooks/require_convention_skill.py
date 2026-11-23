"""PreToolUse hook: backend/·app/ 파일을 고치기 전에 해당 컨벤션 스킬을 읽었는지 검사합니다.

읽지 않았으면 exit 2로 수정을 막고, 이유를 stderr로 Claude에게 돌려줍니다.
검사할 수 없는 경우(입력 형식 오류, transcript 없음)는 작업을 막지 않습니다.
"""

import json
import os
import re
import sys

REQUIRED_SKILLS = {
    "backend": "backend-architecture",
    "app": "react-native-code-standards",
}


def required_skill(file_path, project_dir):
    relative = os.path.relpath(os.path.abspath(file_path), os.path.abspath(project_dir))
    top = relative.split(os.sep, 1)[0]
    return None if top.startswith("..") else REQUIRED_SKILLS.get(top)


def transcript_for(event):
    """코드를 쓰는 에이전트의 transcript. 서브에이전트면 그 서브에이전트 자신의 기록을 봅니다."""
    explicit = event.get("agent_transcript_path")
    if explicit and os.path.exists(explicit):
        return explicit
    main = event.get("transcript_path", "")
    agent_id = event.get("agent_id")
    if agent_id and main:
        sub = os.path.join(main[: -len(".jsonl")], "subagents", f"agent-{agent_id}.jsonl")
        if os.path.exists(sub):
            return sub
    return main


def skill_was_read(transcript, skill):
    """Skill 도구 호출, /스킬 명령, Read 도구로 SKILL.md를 연 기록 중 하나가 있으면 읽은 것으로 봅니다."""
    pattern = re.compile(
        r'"skill":\s*"%s"|<command-name>/%s</command-name>'
        r'|"name":\s*"Read",\s*"input":\s*\{[^}]*"file_path":\s*"[^"]*skills/%s/SKILL\.md"'
        % ((re.escape(skill),) * 3)
    )
    with open(transcript, encoding="utf-8", errors="replace") as lines:
        return any(pattern.search(line) for line in lines)


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    tool_input = event.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path")
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd")
    if not file_path or not project_dir:
        return 0
    skill = required_skill(file_path, project_dir)
    if skill is None:
        return 0
    transcript = transcript_for(event)
    if not transcript or not os.path.exists(transcript):
        return 0
    if skill_was_read(transcript, skill):
        return 0
    top = os.path.relpath(os.path.abspath(file_path), os.path.abspath(project_dir)).split(os.sep, 1)[0]
    print(
        f"{top}/ 파일을 고치기 전에 `{skill}` 스킬을 먼저 읽어야 합니다. "
        f"Skill 도구로 `{skill}`을 불러와 규칙을 확인한 뒤 다시 시도하세요. "
        "(TIKITAKA 컨벤션 강제 hook: .claude/hooks/require_convention_skill.py)",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
