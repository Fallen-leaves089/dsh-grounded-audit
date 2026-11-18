from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = json.loads((ROOT / "skill.json").read_text(encoding="utf-8"))


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class ContractTests(unittest.TestCase):
    def test_manifest_identity(self) -> None:
        self.assertEqual(MANIFEST["name"], "project-health-audit")
        self.assertEqual(MANIFEST["package_name"], "dsh-grounded-audit")
        self.assertEqual(MANIFEST["license"], "Apache-2.0")
        self.assertEqual(MANIFEST["first_host"], "dsh")
        self.assertEqual(MANIFEST["supported_hosts"], ["dsh"])
        self.assertEqual(MANIFEST["host_adapter"], "hosts/dsh.md")
        self.assertEqual(MANIFEST["model_profile"], "models/deepseek.md")
        self.assertEqual(MANIFEST["model_status"], "documented")

    def test_dsh_frontmatter_and_no_tool_preapproval(self) -> None:
        text = read("SKILL.md")
        lines = text.splitlines()
        self.assertEqual(lines[0].strip(), "---")
        self.assertIn("name: project-health-audit", lines)
        self.assertIn("license: Apache-2.0", lines)
        self.assertIn("  version: 0.1.1", lines)
        self.assertNotIn("allowedTools", text)
        self.assertNotIn("allowed-tools", text)
        description_line = next(line for line in lines if line.startswith("description:"))
        description = description_line.split(":", 1)[1].strip()
        self.assertLessEqual(len(description), 500)

    def test_skill_name_follows_dsh_conventions(self) -> None:
        name = MANIFEST["name"]
        self.assertRegex(name, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        self.assertTrue(name.endswith("-audit"))
        self.assertIn(f"显式入口：`/{name}`", read("SKILL.md"))

    def test_host_adapter_contract(self) -> None:
        text = read(MANIFEST["host_adapter"])
        for heading in (
            "## 识别",
            "## 安装位置",
            "## 工具映射",
            "## 权限边界",
            "## 上下文",
            "## 目标文件与不可信内容",
            "## 网络与写入",
            "## 未验证项",
            "## 自检清单",
        ):
            self.assertIn(heading, text)
        for marker in ("不可信", "线索，不单独判定", "未验证", "danger-full-access"):
            self.assertIn(marker, text)
        for tool in (
            "`read`",
            "`glob`",
            "`grep`",
            "`bash`",
            "`job_output`",
            "`todo_write`",
            "`skill`",
            "`subagent`",
            "`web_search`",
            "`web_fetch`",
        ):
            self.assertIn(tool, text)

    def test_model_profile_contract(self) -> None:
        text = read(MANIFEST["model_profile"])
        for heading in (
            "## 风险分层",
            "## 需要重点测试的风险",
            "### 最优先失败模式",
            "## 强制补偿控制",
            "## 行为评测用例",
        ):
            self.assertIn(heading, text)
        self.assertIn("### D1", text)
        self.assertIn("### D9", text)
        for marker in ("风险假设", "不是模型行为已验证", "job_output", "write", "edit"):
            self.assertIn(marker, text)

    def test_feedback_address_is_documented(self) -> None:
        address = "chenshuidelaye@qq.com"
        self.assertIn(address, read("README.md"))
        self.assertIn(address, read(MANIFEST["model_profile"]))

    def test_validation_boundary_is_explicit(self) -> None:
        readme = read("README.md")
        for marker in (
            "## 验证边界与适配状态",
            "确定性检查",
            "不调用真实 DSH",
            "不等于模型行为已验证",
            "tests/model-evals/README.md",
        ):
            self.assertIn(marker, readme)
        evals = read("tests/model-evals/README.md")
        for marker in (
            "## 验证等级",
            "deterministic",
            "documented",
            "observed",
            "validated",
            "宿主版本",
            "权限/沙箱模式",
            "实际工具集",
            "未覆盖项",
        ):
            self.assertIn(marker, evals)

    def test_runtime_required_files_are_subset_of_required_files(self) -> None:
        required = set(MANIFEST["required_files"])
        runtime = set(MANIFEST["runtime_required_files"])
        self.assertTrue(runtime.issubset(required))

    def test_memory_is_external_to_the_skill_root(self) -> None:
        memory = MANIFEST["memory"]
        self.assertEqual(memory["mode"], "external")
        self.assertEqual(memory["local"], "PITFALLS.local.md")
        self.assertTrue(memory["directory"].startswith("$DSH_HOME/"))
        self.assertNotIn("repo", memory)

    def test_no_seeded_memory_or_legacy_corpus(self) -> None:
        self.assertFalse((ROOT / "PITFALLS.md").exists())
        self.assertFalse((ROOT / "PITFALLS.local.md").exists())
        for marker in (
            "windows-" + "pitfalls",
            "macos-" + "pitfalls",
            "linux-server-" + "pitfalls",
            "platform-" + "commands",
        ):
            self.assertFalse(any(ROOT.rglob(marker + "*")))

    def test_skill_references_exist(self) -> None:
        text = read("SKILL.md")
        references = set(re.findall(r"`((?:references|hosts|models|scripts)/[^`]+)`", text))
        for relative in references:
            if "<" in relative or ">" in relative:
                continue
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_no_absolute_user_paths_in_docs(self) -> None:
        patterns = (re.compile(r"[A-Za-z]:\\Users\\"), re.compile(r"/home/"))
        for path in ROOT.rglob("*.md"):
            if "tests" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in patterns:
                self.assertIsNone(pattern.search(text), str(path.relative_to(ROOT)))


if __name__ == "__main__":
    unittest.main()
