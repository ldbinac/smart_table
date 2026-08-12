"""
脚本节点配置校验单元测试
测试 WorkflowService._validate_script_node 对 language/script_source/timeout/
result_variable/branches 的校验逻辑。
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.workflow_service import WorkflowService


class TestValidateScriptNode:
    def _node(self, **overrides):
        config = {
            'language': 'python',
            'script_source': 'set_result(1)',
            'timeout': 30,
            'result_variable': 'script_result',
            'branches': [],
            **overrides,
        }
        return {'node_type': 'script', 'config': config}

    def test_valid_config(self):
        WorkflowService._validate_script_node(self._node(), all_node_ids=set())

    def test_invalid_language(self):
        with pytest.raises(ValueError, match='语言'):
            WorkflowService._validate_script_node(self._node(language='ruby'), all_node_ids=set())

    def test_empty_script(self):
        with pytest.raises(ValueError, match='不能为空'):
            WorkflowService._validate_script_node(self._node(script_source=''), all_node_ids=set())

    def test_oversized_script(self):
        with pytest.raises(ValueError, match='50000'):
            WorkflowService._validate_script_node(self._node(script_source='x' * 50001), all_node_ids=set())

    def test_timeout_out_of_range(self):
        with pytest.raises(ValueError, match='超时'):
            WorkflowService._validate_script_node(self._node(timeout=0), all_node_ids=set())
        with pytest.raises(ValueError, match='超时'):
            WorkflowService._validate_script_node(self._node(timeout=301), all_node_ids=set())

    def test_invalid_result_variable(self):
        with pytest.raises(ValueError, match='变量名'):
            WorkflowService._validate_script_node(self._node(result_variable='123bad'), all_node_ids=set())

    def test_duplicate_branch_labels(self):
        branches = [
            {'label': 'a', 'target_node_id': 'n1'},
            {'label': 'a', 'target_node_id': 'n2'},
        ]
        with pytest.raises(ValueError, match='重复'):
            WorkflowService._validate_script_node(self._node(branches=branches), all_node_ids={'n1', 'n2'})

    def test_branch_target_not_exist(self):
        branches = [{'label': 'a', 'target_node_id': 'missing'}]
        with pytest.raises(ValueError, match='不存在'):
            WorkflowService._validate_script_node(self._node(branches=branches), all_node_ids={'n1'})
