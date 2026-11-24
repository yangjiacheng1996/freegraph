# Specification Quality Checklist: B21F1 · OTLP 导出插件（可选 extra）+ 后端对接文档

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-24
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- 本 spec 按仓库既有惯例（B18F1 / B19F1 / B20F1 / B20F2）包含「形态锁定裁定」节：
  它锁定的是**可判定的外部契约**（extra 名称、依赖许可证、注入点、`Span` → OTLP
  映射表、失败隔离语义），不是代码结构 / 类布局 / SQL / 文件格式构造器。
  Mandatory 的用户场景、Success Criteria 与验收判据仍以**用户可观察结果**表述。
- **Spec 阶段结论**：可行，**不触发 +2 人日上浮**（复用官方 OTLP 编码器
  `encode_spans` + 官方 gRPC stubs `TraceServiceStub`，无自研 protobuf / OTLP 编码；
  **不使用** `OTLPSpanExporter` 门面）。若实测推翻该前提，MUST 按立项书 §7.5 立即上浮并回写结论。
- **治理事项**（合入前 MUST 完成，已在 spec「形态锁定裁定 §6」登记）：
  1. 宪法 v1.7.0「v1.0 无 `[project.optional-dependencies]`」已由 **v1.17.0**
     正式修订为**唯一具名例外**：仅 `[otlp]` 进入 v1.0 发行元数据；基础安装闭包不变。
  2. B3F1 的 G3 extras 白名单 / `extras-v2.toml` / G26 例外名单 / B19F1 import 例外
     **只增不改**的扩充；`protobuf` 的散文许可证标识归一为 SPDX `BSD-3-Clause`
     （不放宽白名单）。
- **已知偏差（已在 spec 登记）**：提示词字面写 `opentelemetry-exporter-otlp`；本 spec
  取同一官方项目的 **gRPC 协议实现** `opentelemetry-exporter-otlp-proto-grpc`，以同时
  满足「官方 OTLP 编码器 / 协议实现复用」与许可证白名单；HTTP-only 后端由用户自装官方 HTTP exporter
  并以 `exporter=` 模式接入。
- **质量门禁 5**：真实模型轮沿用 B19F1 / B20F1 / B20F2 先例，登记偏离并由 B25F1 承接；
  本地图 + fake 模型 + 最小 OTLP 接收端轮照常执行，判据未放宽。
