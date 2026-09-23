"""Keep the localized Beta policy controls and checklist aligned."""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class BetaDiagnosticsPolicyTest(unittest.TestCase):
    def test_locales_share_protocol_controls_and_scenarios(self):
        policies = {
            locale: (ROOT / locale / 'insight/data-collection-policy.mdx').read_text()
            for locale in ('en', 'zh', 'ja')
        }
        expected_scenarios = [f'B2-{number:02}' for number in range(1, 7)]
        expected_config = [
            'space:\n  disable_beta_diagnostics: true',
            'space:\n  disable_telemetry: true',
        ]
        for locale, policy in policies.items():
            with self.subTest(locale=locale):
                self.assertEqual(re.findall(r'`(B2-\d{2})`', policy), expected_scenarios)
                self.assertEqual(re.findall(r'```yaml\n(.*?)\n```', policy, re.S), expected_config)
                for literal in (
                    '4.11.0-beta.2', '1.5', 'instance_id', 'workspace_uuid',
                    'alpha', '30', '90', 'hello@langbot.app', 'traceback',
                    'data/config.yaml', 'SPACE__DISABLE_BETA_DIAGNOSTICS',
                    'SPACE__DISABLE_TELEMETRY', 'space.url', '4.11.0b2+local',
                ):
                    self.assertIn(literal, policy)
                self.assertEqual(len(re.findall(r'^## ', policy, re.M)), 5)

    def test_english_policy_distinguishes_legacy_content_and_diagnostics(self):
        policy = (ROOT / 'en/insight/data-collection-policy.mdx').read_text()
        for required in (
            'pseudonymous identifiers, not anonymous data',
            'legacy `error` field can contain a raw traceback',
            'rules do not sanitize this legacy stream',
            'this release has no stable opt-in',
            'does **not** delete records already received',
            'does not change query telemetry, heartbeat, survey',
            'diagnostics do not automatically run these actions',
            'members explicitly authorized for telemetry access',
            'Ordinary Workspace membership does not itself grant this access',
            'Telemetry read permission alone does not permit deletion',
            'Records become eligible for deletion',
            'not guarantees of deletion at an exact hour',
            'those environment values override the file at startup',
        ):
            self.assertIn(required, policy)

    def test_localized_access_and_cleanup_contract(self):
        required = {
            'en': ('members explicitly authorized for telemetry access',
                   'Telemetry read permission alone does not permit deletion',
                   'Records become eligible for deletion',
                   'not guarantees of deletion at an exact hour'),
            'zh': ('获得明确遥测访问授权的成员', '仅有遥测读取权限不能删除数据',
                   '记录达到阈值后具备删除条件', '并非保证在某个精确时刻完成删除'),
            'ja': ('テレメトリへのアクセスを明示的に許可されたメンバー',
                   'テレメトリの閲覧権限だけでは、削除やエラー状態の変更はできません',
                   'しきい値に達した記録は削除対象',
                   '特定の時刻での削除を保証するものではありません'),
        }
        for locale, clauses in required.items():
            policy = (ROOT / locale / 'insight/data-collection-policy.mdx').read_text()
            with self.subTest(locale=locale):
                for clause in clauses:
                    self.assertIn(clause, policy)

    def test_built_policy_html_when_requested(self):
        import os
        from html.parser import HTMLParser
        if os.environ.get('BETA_DIAGNOSTICS_STATIC') != '1':
            self.skipTest('Run with BETA_DIAGNOSTICS_STATIC=1 after npm run build')

        class VisibleText(HTMLParser):
            def __init__(self):
                super().__init__()
                self.parts = []
                self.tables = 0
                self.hidden = 0

            def handle_starttag(self, tag, attrs):
                if tag in ('script', 'style'):
                    self.hidden += 1
                if tag == 'table':
                    self.tables += 1

            def handle_endtag(self, tag):
                if tag in ('script', 'style'):
                    self.hidden -= 1

            def handle_data(self, data):
                if not self.hidden:
                    self.parts.append(data)

        for locale in ('en', 'zh', 'ja'):
            with self.subTest(locale=locale):
                html = (ROOT / 'dist/public' / locale /
                        'insight/data-collection-policy/index.html').read_text()
                parser = VisibleText()
                parser.feed(html)
                text = ''.join(parser.parts)
                self.assertEqual(parser.tables, 2)
                for literal in ('4.11.0-beta.2', 'disable_beta_diagnostics',
                                'disable_telemetry', 'SPACE__DISABLE_BETA_DIAGNOSTICS',
                                'SPACE__DISABLE_TELEMETRY', '4.11.0b2+local',
                                'instance_id', 'workspace_uuid', 'traceback'):
                    self.assertIn(literal, text)
                for number in range(1, 7):
                    self.assertIn(f'B2-{number:02}', text)
                self.assertIn('href="mailto:hello@langbot.app"', html)


if __name__ == '__main__':
    unittest.main()
