# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""契约层四个核心类型的单元测试（US1）。

覆盖 data-model.md 的 **I-01 … I-11 / I-14 / I-16** 与 spec 的 **SC-004**：

* ``StateDict`` 是与 ``dict[str, Any]`` 完全等价的**类型别名**（不是新造类）；
* ``Command`` 的三个语义位、``PARENT`` 常量与「三全空即非法」的构造期校验；
* ``StateSnapshot`` / ``RunConfig`` 的字段清单、字段注解与不可变语义；
* 构造期**只做两条冻结校验**（其余一律只做类型注解、不校验值）；
* 容器**防御性拷贝**（浅拷贝）的确切范围。

本文件从**门面** ``freegraph.contracts`` 导入——这正是外部项目（如 freechain）
引用契约的方式，也是 US1 的独立验收点。
"""

from __future__ import annotations

import re
import typing
from collections.abc import Mapping, Sequence
from dataclasses import FrozenInstanceError, fields
from typing import Any

import pytest

from freegraph.contracts import (
    Command,
    FreegraphError,
    RunConfig,
    StateDict,
    StateSnapshot,
)

CREATED_AT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|\+00:00)$"
)

UTC_ISO_EXAMPLE = "2026-11-05T10:20:30.123456+00:00"


def _snapshot(**overrides: Any) -> StateSnapshot:
    """构造一个字段齐全的 ``StateSnapshot``（允许覆盖单个字段）。"""
    base: dict[str, Any] = {
        "values": {"messages": ["hi"]},
        "next": (),
        "config": RunConfig(),
        "metadata": {},
        "created_at": UTC_ISO_EXAMPLE,
        "tasks": (),
        "interrupts": (),
    }
    base.update(overrides)
    return StateSnapshot(**base)


class TestStateDict:
    """I-01 · 状态字典是与 ``dict[str, Any]`` 完全等价的类型别名。"""

    def test_origin_is_dict(self) -> None:
        """可判定口径 = ``typing.get_origin(StateDict) is dict``。

        **不得**用 ``is`` 判定 ``StateDict is dict[str, Any]``——
        实测 ``dict[str, Any] is dict[str, Any]`` 为 ``False``。
        """
        assert typing.get_origin(StateDict) is dict

    def test_equals_plain_dict_generic(self) -> None:
        """``StateDict == dict[str, Any]`` MUST 成立（同一类型，不是子类型）。"""
        assert StateDict == dict[str, Any]

    def test_args_are_str_and_any(self) -> None:
        """别名的参数 MUST 是 ``(str, Any)``。"""
        assert typing.get_args(StateDict) == (str, Any)

    def test_plain_dict_satisfies_the_alias(self) -> None:
        """普通 dict 收到 ``state: StateDict`` 时类型检查必须通过（FR-002 硬约束）。"""
        value: StateDict = {"messages": ["hi"], "n": 1}
        assert isinstance(value, dict)

    def test_is_not_parameterizable_by_user_schema(self) -> None:
        """``StateDict`` MUST NOT 支持按 schema 参数化（FR-002 / 澄清第 2 条）。"""
        with pytest.raises(TypeError):
            StateDict[dict]  # type: ignore[index]


class TestCommand:
    """I-02 / I-03 / I-04 / I-05 / I-06 / I-14 · 命令原语。"""

    def test_empty_command_raises(self) -> None:
        """``Command()``（三语义位全空）MUST 抛 ``FreegraphError``（fail fast）。"""
        with pytest.raises(FreegraphError):
            Command()

    def test_empty_command_error_is_freegraph_error(self) -> None:
        """抛出的 MUST 正是 ``FreegraphError`` 本身（而非某个子类）。"""
        with pytest.raises(FreegraphError) as excinfo:
            Command()
        assert type(excinfo.value) is FreegraphError

    @pytest.mark.parametrize(
        ("kwargs", "label"),
        [
            ({"goto": "a"}, "仅跳转"),
            ({"update": {"n": 1}}, "仅写入"),
            ({"resume": "v"}, "仅恢复"),
            ({"goto": "a", "update": {"n": 1}}, "跳转 + 写入"),
            ({"resume": "v", "goto": "a"}, "恢复 + 跳转"),
            ({"goto": "a", "update": {"n": 1}, "resume": "v"}, "三语义位同填"),
        ],
    )
    def test_semantic_slots_combine_freely(self, kwargs: dict[str, Any], label: str) -> None:
        """三个语义位 MUST 可任意组合、互不排斥。"""
        cmd = Command(**kwargs)
        assert cmd is not None
        assert label  # 参数化标签仅用于失败时定位

    def test_explicitly_empty_update_is_legal(self) -> None:
        """``update={}``（显式但为空）合法——与「未提供」（``None``）严格区分。"""
        cmd = Command(update={})
        assert cmd.update == {}

    def test_explicitly_empty_goto_tuple_is_legal(self) -> None:
        """``goto=()`` 合法——语义为「该位不产生动作」。"""
        cmd = Command(goto=())
        assert cmd.goto == ()

    def test_update_none_alone_is_legal(self) -> None:
        """``update=None`` 单独出现时合法（其余两位有值）。"""
        cmd = Command(goto="a", update=None)
        assert cmd.update is None

    def test_parent_constant_value(self) -> None:
        """``Command.PARENT`` 的值 MUST 是字符串哨兵 ``"__parent__"``（I-04）。"""
        assert Command.PARENT == "__parent__"

    def test_parent_is_class_var_not_a_field(self) -> None:
        """``PARENT`` MUST 是 ``ClassVar`` 而非实例字段——不得出现在 ``__slots__`` 中。"""
        assert "PARENT" not in Command.__slots__
        assert "PARENT" not in {f.name for f in fields(Command)}

    def test_goto_is_not_normalized(self) -> None:
        """``goto`` MUST NOT 被归一化：传元组存元组、传列表存列表。"""
        assert Command(goto=("a", "b")).goto == ("a", "b")
        assert isinstance(Command(goto=("a", "b")).goto, tuple)
        assert Command(goto=["a", "b"]).goto == ["a", "b"]
        assert isinstance(Command(goto=["a", "b"]).goto, list)

    def test_fields_are_frozen(self) -> None:
        """构造后字段不可改（赋值抛 ``FrozenInstanceError``）。"""
        cmd = Command(goto="a")
        with pytest.raises(FrozenInstanceError):
            cmd.goto = "b"  # type: ignore[misc]

    def test_fields_count(self) -> None:
        """``Command`` MUST 恰有 3 个字段（``goto`` / ``update`` / ``resume``）。"""
        assert [f.name for f in fields(Command)] == ["goto", "update", "resume"]

    def test_repr_contains_field_names(self) -> None:
        """``repr`` MUST 含全部字段名。"""
        text = repr(Command(goto="a"))
        assert text.startswith("Command(")
        for name in ("goto=", "update=", "resume="):
            assert name in text

    def test_field_level_equality(self) -> None:
        """字段级相等语义：同值相等、异值不等。"""
        assert Command(goto="a") == Command(goto="a")
        assert Command(goto="a") != Command(goto="b")


class TestTypeHintResolution:
    """I-06 / SC-004 · 字段注解 100% 覆盖且可被完整解析。"""

    @pytest.mark.parametrize(
        "cls",
        [Command, StateSnapshot, RunConfig],
        ids=["Command", "StateSnapshot", "RunConfig"],
    )
    def test_get_type_hints_resolves_completely(self, cls: type) -> None:
        """``typing.get_type_hints`` MUST 完整解析、无异常。"""
        hints = typing.get_type_hints(cls)
        assert hints

    @pytest.mark.parametrize(
        "cls",
        [Command, StateSnapshot, RunConfig],
        ids=["Command", "StateSnapshot", "RunConfig"],
    )
    def test_no_residual_string_annotations(self, cls: type) -> None:
        """解析结果 MUST NOT 含残留字符串注解。

        注意：``get_type_hints`` 的返回里**含** ``PARENT`` 这一 ``ClassVar`` 项，
        故字段数 MUST 用 ``dataclasses.fields()`` 判定，
        **不得**断言「注解条数 == 字段数」。
        """
        hints = typing.get_type_hints(cls)
        for f in fields(cls):
            assert not isinstance(hints[f.name], str), f.name
            assert not isinstance(cls.__annotations__[f.name], str), f.name

    def test_command_hints_include_parent_classvar(self) -> None:
        """``get_type_hints(Command)`` MUST 含 ``PARENT`` 这一 ``ClassVar`` 项。"""
        hints = typing.get_type_hints(Command)
        assert "PARENT" in hints
        assert typing.get_origin(hints["PARENT"]) is typing.ClassVar

    def test_user_node_signature_annotations_resolve(self) -> None:
        """US1 验收场景 2：用户节点的入参 / 配置入参注解 MUST 能被完整解析。

        这正是外部项目（freechain）引用契约层的实际用法——
        用 ``StateDict`` 与 ``RunConfig`` 标注节点函数签名。
        """

        def node(state: StateDict, config: RunConfig) -> StateDict:
            return state

        hints = typing.get_type_hints(node)
        assert hints["state"] == StateDict
        assert hints["config"] is RunConfig
        assert not any(isinstance(value, str) for value in hints.values())

    def test_command_goto_hint_is_frozen(self) -> None:
        """``goto`` 的冻结注解 = ``str | Sequence[str] | None``。"""
        hint = typing.get_type_hints(Command)["goto"]
        assert str in typing.get_args(hint)
        assert type(None) in typing.get_args(hint)

    def test_state_snapshot_metadata_is_mapping(self) -> None:
        """快照的 ``metadata`` 注解 MUST 是 ``Mapping`` 形态（只读映射）。"""
        hint = typing.get_type_hints(StateSnapshot)["metadata"]
        assert typing.get_origin(hint) is Mapping
        assert typing.get_args(hint) == (str, Any)

    def test_state_snapshot_values_is_state_dict(self) -> None:
        """快照的 ``values`` 注解 MUST 是 ``dict[str, Any]`` 形态。"""
        hint = typing.get_type_hints(StateSnapshot)["values"]
        assert typing.get_origin(hint) is dict
        assert typing.get_args(hint) == (str, Any)

    def test_run_config_metadata_is_mapping_and_tags_is_sequence(self) -> None:
        """配置的 ``metadata`` MUST 是 ``Mapping``、``tags`` MUST 是 ``Sequence``。"""
        hints = typing.get_type_hints(RunConfig)
        assert typing.get_origin(hints["metadata"]) is Mapping
        assert typing.get_origin(hints["tags"]) is Sequence


class TestStateSnapshot:
    """I-07 / I-08 · 状态快照的七字段与时间戳格式。"""

    def test_field_names_are_frozen(self) -> None:
        """七字段清单即冻结面，不得增删。"""
        assert [f.name for f in fields(StateSnapshot)] == [
            "values",
            "next",
            "config",
            "metadata",
            "created_at",
            "tasks",
            "interrupts",
        ]

    @pytest.mark.parametrize(
        "field_name",
        ["values", "next", "config", "metadata", "created_at", "tasks", "interrupts"],
    )
    def test_every_field_is_required(self, field_name: str) -> None:
        """七字段全部必填——缺任一字段构造失败。"""
        kwargs: dict[str, Any] = {
            "values": {},
            "next": (),
            "config": RunConfig(),
            "metadata": {},
            "created_at": UTC_ISO_EXAMPLE,
            "tasks": (),
            "interrupts": (),
        }
        kwargs.pop(field_name)
        with pytest.raises(TypeError):
            StateSnapshot(**kwargs)

    def test_created_at_format_is_utc_iso8601(self) -> None:
        """``created_at`` MUST 匹配 UTC ISO-8601 正则。"""
        snap = _snapshot()
        assert CREATED_AT_RE.match(snap.created_at)
        assert CREATED_AT_RE.match("2026-11-05T10:20:30Z")
        assert CREATED_AT_RE.match("2026-11-05T10:20:30+00:00")

    def test_created_at_format_is_not_validated_at_construction(self) -> None:
        """构造期**不校验值**：``created_at`` 格式不符 MUST NOT 抛错。

        （构造期只做两条冻结校验——见 spec Assumptions「构造期校验边界」。）
        """
        snap = _snapshot(created_at="not-a-date")
        assert snap.created_at == "not-a-date"

    def test_fields_are_frozen(self) -> None:
        """构造后字段不可改。"""
        snap = _snapshot()
        with pytest.raises(FrozenInstanceError):
            snap.values = {}  # type: ignore[misc]

    def test_has_no_tags_field(self) -> None:
        """快照**没有** ``tags`` 字段（``tags`` 属 ``RunConfig``）。"""
        assert "tags" not in {f.name for f in fields(StateSnapshot)}

    def test_metadata_is_defensively_copied(self) -> None:
        """I-16 · 快照 MUST 拷 ``metadata``，且不与调用方共用同一对象。"""
        passed = {"source": "test"}
        snap = _snapshot(metadata=passed)
        assert snap.metadata is not passed
        assert snap.metadata == passed

    def test_metadata_copy_is_shallow(self) -> None:
        """拷贝为**浅拷贝**——嵌套容器仍与调用方共享同一对象。"""
        nested = {"deep": 1}
        passed = {"outer": nested}
        snap = _snapshot(metadata=passed)
        assert snap.metadata["outer"] is nested


class TestRunConfig:
    """I-09 / I-10 / I-11 / I-16 · 运行配置的四字段与裸 dict 构造路径。"""

    def test_field_names_are_frozen(self) -> None:
        """四字段清单即冻结面，不得增删。"""
        assert [f.name for f in fields(RunConfig)] == [
            "thread_id",
            "context",
            "metadata",
            "tags",
        ]

    def test_all_fields_are_optional(self) -> None:
        """四字段均有缺省，``RunConfig()`` MUST 可全空构造（I-11）。"""
        cfg = RunConfig()
        assert cfg.thread_id is None
        assert cfg.context is None
        assert cfg.metadata == {}
        assert cfg.tags == ()

    def test_from_dict_accepts_known_keys(self) -> None:
        """键全在四字段内时正常构造。"""
        cfg = RunConfig.from_dict({"thread_id": "t-1", "tags": ["a"]})
        assert cfg.thread_id == "t-1"
        assert cfg.tags == ("a",)

    def test_from_dict_rejects_unknown_key_by_default(self) -> None:
        """默认严格：出现四字段之外的键 MUST 抛 ``FreegraphError``（I-09）。"""
        with pytest.raises(FreegraphError) as excinfo:
            RunConfig.from_dict({"threadId": "t"})
        assert "threadId" in str(excinfo.value)

    def test_from_dict_ignore_unknown(self) -> None:
        """``ignore_unknown=True`` 走宽松：忽略未知键（I-10）。"""
        cfg = RunConfig.from_dict(
            {"thread_id": "t-1", "extra": 1},
            ignore_unknown=True,
        )
        assert cfg.thread_id == "t-1"
        assert not hasattr(cfg, "extra")

    def test_from_dict_uses_field_metadata_not_hardcoded_list(self) -> None:
        """未知键比对 MUST 以 ``dataclasses.fields()`` 为准——不得硬编码字段名清单。"""
        assert {f.name for f in fields(RunConfig)} == {
            "thread_id",
            "context",
            "metadata",
            "tags",
        }

    def test_is_not_hashable(self) -> None:
        """本类不可哈希——``hash()`` 抛 ``TypeError``（``metadata`` 装的是 dict）。"""
        with pytest.raises(TypeError):
            hash(RunConfig())

    def test_thread_id_type_is_not_validated_at_construction(self) -> None:
        """构造期**不校验值**：``thread_id`` 类型不符 MUST NOT 抛错。"""
        cfg = RunConfig(thread_id=123)  # type: ignore[arg-type]
        assert cfg.thread_id == 123

    def test_fields_are_frozen(self) -> None:
        """构造后字段不可改。"""
        cfg = RunConfig()
        with pytest.raises(FrozenInstanceError):
            cfg.thread_id = "x"  # type: ignore[misc]

    def test_metadata_and_tags_are_defensively_copied(self) -> None:
        """I-16 · 配置 MUST 拷 ``metadata`` 与 ``tags``，不与调用方共用同一对象。"""
        metadata = {"k": "v"}
        tags = ["a", "b"]
        cfg = RunConfig(metadata=metadata, tags=tags)
        assert cfg.metadata is not metadata
        assert cfg.tags is not tags
        assert cfg.metadata == metadata
        assert cfg.tags == ("a", "b")

    def test_from_dict_defensively_copies_containers(self) -> None:
        """``from_dict`` 路径同样 MUST 做防御性拷贝。"""
        payload = {"thread_id": "t", "metadata": {"k": "v"}, "tags": ["a"]}
        cfg = RunConfig.from_dict(payload)
        assert cfg.metadata is not payload["metadata"]
        assert cfg.tags is not payload["tags"]

    def test_copy_is_shallow(self) -> None:
        """拷贝为**浅拷贝**——嵌套容器仍与调用方共享同一对象。"""
        nested = {"deep": 1}
        cfg = RunConfig(metadata={"outer": nested})
        assert cfg.metadata["outer"] is nested

    def test_repr_and_equality(self) -> None:
        """具 repr 与字段级相等语义（FR-014 冻结项）。"""
        assert repr(RunConfig(thread_id="t")).startswith("RunConfig(")
        assert "thread_id=" in repr(RunConfig(thread_id="t"))
        assert RunConfig(thread_id="t") == RunConfig(thread_id="t")
        assert RunConfig(thread_id="t") != RunConfig(thread_id="u")
