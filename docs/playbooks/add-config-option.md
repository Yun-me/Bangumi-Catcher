# 新增配置项

## 1. 加字段

`src/bangumi_catcher/core/config/models.py` 对应的 `*Config`：

```python
class AnalysisConfig(BaseModel):
    ...
    min_rating: int = Field(default=0, ge=0, le=10)
```

规则：

- 必须有默认值，旧配置才能继续工作。
- 用 Pydantic 约束（`ge/le`、`Literal`）而不是手写 if。
- 危险的输入在 `field_validator(mode="before")` 中收敛或给出中文错误。
- 需要设备相关路径时放到 `paths.py`，不要在模型里读 `cwd`。

## 2. 示例与文档

1. `config.yaml`：加字段与一行中文注释。
2. `docs/configuration.md`：加到对应字段表。
3. 如果用户应在 GUI 修改：`ui/settings_dialog.py` 增加控件，并在 `_save()` 写回。

环境变量不需要额外代码：`BANGUMI_ANALYSIS__MIN_RATING=7` 会自动映射。

## 3. 使用

配置对象通过参数传递，例如 `analyze_user_collection(collection, config)`。
不要新增全局单例。新增参数时保持旧签名兼容（默认值来自 config）。

## 4. 测试

`tests/unit/core/test_config.py` 至少覆盖：

- 默认值；
- 环境变量覆盖（可加到参数化用例）；
- 非法值被拒绝或收敛；
- 显式配置文件合并。

若配置影响分析结果，在对应单元测试里用 `AppConfig(...)` 构造非默认值并断言行为。

## 5. 验证

```bash
python -m bangumi_catcher.cli config --json | grep -i min_rating
python scripts/dev.py check
```

## 6. 兼容性

- 删除/重命名字段是破坏性变更：需要 major 版本 + 迁移文档 + 兼容读取逻辑。
- 新增字段是 minor 变更；在 `CHANGELOG.md` 的 `Added` 下记录。
