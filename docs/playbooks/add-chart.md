# 新增图表维度

目标：在 GUI 的“数据洞察”下拉框和 HTML 报告中同时出现一个新图表。

## 1. 确认数据已在报告里

图表只能消费 `AnalysisReport` 字段。若需要新统计：

1. 在 `core/models/report.py` 增加行模型/字段。
2. 在 `core/analysis.py` 的单次遍历中填充，避免二次遍历。
3. 在 `tests/unit/core/test_analysis.py` 补口径测试（空数据、边界值）。

## 2. 加标题

`src/bangumi_catcher/charts/catalog.py`：

```python
CHART_TITLES = {
    ...,
    "rating_heatmap": "评分热力图",
}
```

这个模块**不能**导入 Matplotlib，UI 启动时会导入它。

## 3. 写构建器

`src/bangumi_catcher/charts/builders.py`：

```python
def make_rating_heatmap(report: AnalysisReport, theme: Theme = LIGHT) -> Figure:
    data = report.some_field
    if not data:
        return empty_figure("评分热力图", theme)
    figure, axes = create_figure(theme)
    ...
    set_title(axes, "评分热力图", theme)
    apply_cjk_font(axes)
    return figure
```

并注册：

```python
FIGURE_BUILDERS = {
    ...,
    "rating_heatmap": make_rating_heatmap,
}
```

规则：

- 无数据时返回 `empty_figure(...)`，不要抛异常。
- 颜色用 `charts.theme` 的 `PALETTE` / `ACCENT`；不要硬编码主题色。
- 不在构建器里写文件、不访问 Qt、不使用全局状态。

## 4. 测试

`tests/unit/charts/test_render.py` 已有的断言会自动覆盖：

- `set(FIGURE_BUILDERS) == set(CHART_TITLES)`（漏注册会失败）；
- `len(FIGURE_BUILDERS) == 9`（新增图表后把 9 改成 10）；
- `render_all` 返回 9/10 个 data URI；
- 渲染结果以 PNG 签名开头。

再补一个空数据测试，确认不会崩溃。

## 5. 模板

`src/bangumi_catcher/templates/report.html.j2` 增加卡片：

```jinja
{% if charts.rating_heatmap %}
<div class="card"><h3>评分热力图</h3><img src="{{ charts.rating_heatmap }}" alt="评分热力图"></div>
{% endif %}
```

key 必须与 `FIGURE_BUILDERS` / `CHART_TITLES` 一致。

## 6. 验证

```bash
python scripts/dev.py test -- tests/unit/charts
python scripts/dev.py check
python -m bangumi_catcher     # 切换到“数据洞察”确认下拉框与渲染
python -m bangumi_catcher.cli analyze snapshot.json --format html -o report.html
```

## 7. 文档

- 更新 `docs/data-model.md` 的统计说明（如新增口径）。
- 更新 `CHANGELOG.md` 的 `Unreleased`。
