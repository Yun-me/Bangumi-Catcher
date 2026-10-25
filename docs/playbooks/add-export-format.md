# 新增导出格式

以新增 `xlsx` 为例。导出必须原子化，并且 GUI 与 CLI 共用同一条路径。

## 1. 写 writer

在 `src/bangumi_catcher/reporting/xlsx_export.py`：

```python
from pathlib import Path
from ..core.models import UserCollection

def collection_to_xlsx(collection: UserCollection, output_path: str | Path) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ...  # 只负责写文件，不处理原子替换
    return str(path)
```

writer 的契约：接收一个**临时文件路径**，写完即可；不要自己 `os.replace`。
如果要引入新依赖（如 openpyxl），先写 ADR 并更新 `pyproject.toml`。

## 2. 暴露与注册

`src/bangumi_catcher/reporting/__init__.py` 导出函数。

`src/bangumi_catcher/services/export.py`：

```python
EXPORT_FORMATS = ("csv", "json", "report-json", "html", "xlsx")

def export_extension(format_name: str) -> str:
    if format_name == "report-json":
        return "json"
    return format_name
```

在 `export_dataset` 的分派里加分支（仍在 `atomic_output` 上下文内）：

```python
elif format_name == "xlsx":
    collection_to_xlsx(collection, temporary)
```

## 3. 接入口

- CLI：`cli/parser.py` 的 `--format` 直接引用 `EXPORT_FORMATS`，无需改。
- GUI：`ui/main_window.py` 的 `EXPORT_MENU` 增加 `("xlsx", "Excel 表格")`；
  筛选导出菜单在 `ui/library_page.py` 按需添加。
- `default_output_path` / `export_stem` 会自动给出文件名；如需特殊命名再扩展。

## 4. 测试

`tests/unit/reporting/test_exporters.py` 加 writer 单元测试（内容、表头、特殊字符）。
`tests/integration/test_export.py` 的 `@pytest.mark.parametrize("format_name", EXPORT_FORMATS)`
会自动覆盖：父目录创建、临时文件清理、目标文件存在。若新格式需要额外断言，
在该测试里加分支。

另外确认：

- 取消/失败时旧文件不被覆盖（复用现有 `cancel_before_commit` 测试）；
- CSV 的公式注入防护只适用于文本格式，Excel writer 也要考虑公式前缀；
- 大收藏（万级）内存占用可接受。

## 5. 文档与验证

- 更新 `README.md` 的导出格式列表。
- 更新 `docs/architecture.md` / `docs/packaging.md`（如新增依赖或包数据）。
- `CHANGELOG.md` 的 `Unreleased`。
- 跑 `python scripts/dev.py check`，再手动导出一次确认可打开。
