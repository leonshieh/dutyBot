import pandas as pd
import numpy as np

NODE_REGISTRY = {}  # {node_type: {"execute": func, "params_schema": {...}}}


def _parse_datetime_col(series):
    """统一日期解析，支持 2026/4/23 19:00:00 等混合格式"""
    parsed = pd.to_datetime(series, errors="coerce")
    if parsed.isna().any():
        for fmt in ['%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d', '%Y-%m-%d']:
            mask = parsed.isna()
            if not mask.any():
                break
            retry = pd.to_datetime(series[mask], format=fmt, errors="coerce")
            parsed[mask] = retry
    return parsed


def register_node(node_type, params_schema):
    """装饰器，注册节点"""
    def decorator(func):
        NODE_REGISTRY[node_type] = {
            "execute": func,
            "params_schema": params_schema
        }
        return func
    return decorator


# ============================================================
# 文本类操作
# ============================================================

@register_node("text_filter", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "keyword": {"type": "str", "required": True, "label": "关键词"}
})
def execute_text_filter(df, params):
    column = params["column"]
    keyword = params["keyword"]
    if column not in df.columns:
        raise ValueError(f"列 '{column}' 不存在")
    return df[df[column].astype(str).str.contains(keyword, case=False, na=False)]


@register_node("text_replace", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "old": {"type": "str", "required": True, "label": "原文本"},
    "new": {"type": "str", "required": True, "label": "新文本"}
})
def execute_text_replace(df, params):
    column = params["column"]
    old = params["old"]
    new = params["new"]
    if column not in df.columns:
        raise ValueError(f"列 '{column}' 不存在")
    df = df.copy()
    df[column] = df[column].astype(str).str.replace(old, new, regex=False)
    return df


@register_node("text_slice", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "start": {"type": "int", "required": True, "label": "起始位置"},
    "end": {"type": "int", "required": True, "label": "结束位置"}
})
def execute_text_slice(df, params):
    column = params["column"]
    start = params["start"]
    end = params["end"]
    if column not in df.columns:
        raise ValueError(f"列 '{column}' 不存在")
    df = df.copy()
    df[column] = df[column].astype(str).str[start:end]
    return df


@register_node("text_trim", {
    "column": {"type": "str", "required": True, "label": "列名"}
})
def execute_text_trim(df, params):
    column = params["column"]
    if column not in df.columns:
        raise ValueError(f"列 '{column}' 不存在")
    df = df.copy()
    df[column] = df[column].astype(str).str.strip()
    return df


@register_node("text_case", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "mode": {"type": "str", "required": True, "label": "转换模式", "options": ["upper", "lower", "title"]}
})
def execute_text_case(df, params):
    column = params["column"]
    mode = params["mode"]
    if column not in df.columns:
        raise ValueError(f"列 '{column}' 不存在")
    df = df.copy()
    s = df[column].astype(str).str
    if mode == "upper":
        df[column] = s.upper()
    elif mode == "lower":
        df[column] = s.lower()
    elif mode == "title":
        df[column] = s.title()
    else:
        raise ValueError(f"不支持的大小写模式: '{mode}'，可选: upper/lower/title")
    return df


@register_node("regex_extract", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "pattern": {"type": "str", "required": True, "label": "正则表达式"},
    "new_col": {"type": "str", "required": False, "label": "新列名"}
})
def execute_regex_extract(df, params):
    column = params["column"]
    pattern = params["pattern"]
    new_col = params.get("new_col") or column + "_extracted"
    if column not in df.columns:
        raise ValueError(f"列 '{column}' 不存在")
    df = df.copy()
    df[new_col] = df[column].astype(str).str.extract(pattern, expand=False)
    return df


# ============================================================
# 数值类操作
# ============================================================

@register_node("num_filter", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "operator": {"type": "str", "required": True, "label": "运算符", "options": [">", "<", "=", ">=", "<=", "!="]},
    "value": {"type": "float", "required": True, "label": "数值"}
})
def execute_num_filter(df, params):
    column = params["column"]
    operator = params["operator"]
    value = params["value"]
    if column not in df.columns:
        raise ValueError(f"列 '{column}' 不存在")
    ops = {
        ">": lambda c, v: c > v,
        "<": lambda c, v: c < v,
        "=": lambda c, v: c == v,
        ">=": lambda c, v: c >= v,
        "<=": lambda c, v: c <= v,
        "!=": lambda c, v: c != v,
    }
    if operator not in ops:
        raise ValueError(f"不支持的运算符: '{operator}'，可选: >/</=/>=/<=/!=")
    mask = ops[operator](pd.to_numeric(df[column], errors="coerce"), value)
    return df[mask]


@register_node("num_arithmetic", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "operator": {"type": "str", "required": True, "label": "运算符", "options": ["+", "-", "*", "÷"]},
    "value": {"type": "float", "required": True, "label": "数值"}
})
def execute_num_arithmetic(df, params):
    column = params["column"]
    operator = params["operator"]
    value = params["value"]
    if column not in df.columns:
        raise ValueError(f"列 '{column}' 不存在")
    df = df.copy()
    numeric_col = pd.to_numeric(df[column], errors="coerce")
    if operator == "+":
        df[column] = numeric_col + value
    elif operator == "-":
        df[column] = numeric_col - value
    elif operator == "*":
        df[column] = numeric_col * value
    elif operator == "÷":
        if value == 0:
            raise ValueError("除数不能为 0")
        df[column] = numeric_col / value
    else:
        raise ValueError(f"不支持的运算符: '{operator}'，可选: +/-/*/÷")
    return df


@register_node("num_round", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "decimals": {"type": "int", "required": True, "label": "小数位数"}
})
def execute_num_round(df, params):
    column = params["column"]
    decimals = params["decimals"]
    if column not in df.columns:
        raise ValueError(f"列 '{column}' 不存在")
    df = df.copy()
    df[column] = df[column].round(decimals)
    return df


@register_node("num_aggregate", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "func": {"type": "str", "required": True, "label": "聚合函数", "options": ["sum", "avg", "max", "min", "count"]}
})
def execute_num_aggregate(df, params):
    column = params["column"]
    func = params["func"]
    if column not in df.columns:
        raise ValueError(f"列 '{column}' 不存在")
    numeric_col = pd.to_numeric(df[column], errors="coerce")
    func_map = {
        "sum": lambda c: c.sum(),
        "avg": lambda c: c.mean(),
        "max": lambda c: c.max(),
        "min": lambda c: c.min(),
        "count": lambda c: c.count(),
    }
    if func not in func_map:
        raise ValueError(f"不支持的聚合函数: '{func}'，可选: sum/avg/max/min/count")
    result = func_map[func](numeric_col)
    # 不改变 df 的行列，仅附加 attrs
    if "aggregate_result" not in df.attrs:
        df.attrs["aggregate_result"] = {}
    if column not in df.attrs["aggregate_result"]:
        df.attrs["aggregate_result"][column] = {}
    df.attrs["aggregate_result"][column][func] = result
    return df


# ============================================================
# 日期类操作
# ============================================================

@register_node("date_format", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "format": {"type": "str", "required": True, "label": "格式字符串"}
})
def execute_date_format(df, params):
    column = params["column"]
    fmt = params["format"]
    if column not in df.columns:
        raise ValueError(f"列 '{column}' 不存在")
    df = df.copy()
    df[column] = _parse_datetime_col(df[column]).dt.strftime(fmt)
    return df


@register_node("date_extract", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "part": {"type": "str", "required": True, "label": "提取部分", "options": ["year", "month", "day", "weekday"]},
    "new_col": {"type": "str", "required": False, "label": "新列名"}
})
def execute_date_extract(df, params):
    column = params["column"]
    part = params["part"]
    new_col = params.get("new_col") or column + "_" + part
    if column not in df.columns:
        raise ValueError(f"列 '{column}' 不存在")
    df = df.copy()
    dt_series = _parse_datetime_col(df[column]).dt
    extract_map = {
        "year": lambda s: s.year,
        "month": lambda s: s.month,
        "day": lambda s: s.day,
        "weekday": lambda s: s.dayofweek,
    }
    if part not in extract_map:
        raise ValueError(f"不支持的日期部分: '{part}'，可选: year/month/day/weekday")
    df[new_col] = extract_map[part](dt_series)
    return df


# ============================================================
# 列操作
# ============================================================

@register_node("date_filter", {
    "column": {"type": "str", "required": True, "label": "日期列"},
    "operator": {"type": "str", "required": True, "label": "筛选方式", "options": ["大于", "小于", "等于", "日期范围内"]},
    "date1": {"type": "str", "required": True, "label": "日期"},
    "date2": {"type": "str", "required": False, "label": "结束日期（between时）"},
})
def execute_date_filter(df, params):
    column = params["column"]
    operator = params["operator"]
    date1 = params["date1"]
    date2 = params.get("date2", "")
    if column not in df.columns:
        raise ValueError(f"列 '{column}' 不存在")
    df = df.copy()
    dt_series = _parse_datetime_col(df[column])
    d1 = pd.Timestamp(date1)
    if operator in ("大于", "gt"):
        df = df[dt_series > d1]
    elif operator in ("小于", "lt"):
        df = df[dt_series < d1]
    elif operator in ("等于", "eq"):
        df = df[dt_series.dt.date == d1.date()]
    elif operator in ("日期范围内", "between"):
        if not date2:
            raise ValueError("between 模式需要提供结束日期")
        d2 = pd.Timestamp(date2)
        df = df[(dt_series >= d1) & (dt_series <= d2)]
    else:
        raise ValueError(f"不支持的筛选方式: '{operator}'")
    return df


# ============================================================
# 列操作
# ============================================================

@register_node("col_delete", {
    "column": {"type": "str_or_list", "required": True, "label": "列名"}
})
def execute_col_delete(df, params):
    column = params["column"]
    if isinstance(column, str):
        cols_to_check = [column]
        cols_to_drop = [column]
    else:
        cols_to_check = column
        cols_to_drop = column
    for col in cols_to_check:
        if col not in df.columns:
            raise ValueError(f"列 '{col}' 不存在")
    return df.drop(columns=cols_to_drop)


@register_node("col_rename", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "new_name": {"type": "str", "required": True, "label": "新列名"}
})
def execute_col_rename(df, params):
    column = params["column"]
    new_name = params["new_name"]
    if column not in df.columns:
        raise ValueError(f"列 '{column}' 不存在")
    return df.rename(columns={column: new_name})


@register_node("col_split", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "delimiter": {"type": "str", "required": True, "label": "分隔符"},
    "new_cols": {"type": "list", "required": False, "label": "新列名列表"}
})
def execute_col_split(df, params):
    column = params["column"]
    delimiter = params["delimiter"]
    new_cols = params.get("new_cols")
    if column not in df.columns:
        raise ValueError(f"列 '{column}' 不存在")
    df = df.copy()
    split_result = df[column].astype(str).str.split(delimiter, expand=True)
    if new_cols:
        # 只取 new_cols 数量的列
        for i, name in enumerate(new_cols):
            if i < split_result.shape[1]:
                df[name] = split_result[i]
            else:
                df[name] = None
    else:
        for i in range(split_result.shape[1]):
            df[f"{column}_{i+1}"] = split_result[i]
    return df


@register_node("col_merge", {
    "columns": {"type": "list", "required": True, "label": "列名列表"},
    "delimiter": {"type": "str", "required": True, "label": "分隔符"},
    "new_col": {"type": "str", "required": True, "label": "新列名"}
})
def execute_col_merge(df, params):
    columns = params["columns"]
    delimiter = params["delimiter"]
    new_col = params["new_col"]
    for col in columns:
        if col not in df.columns:
            raise ValueError(f"列 '{col}' 不存在")
    df = df.copy()
    df[new_col] = df[columns].astype(str).apply(lambda row: delimiter.join(row), axis=1)
    return df


@register_node("col_calc", {
    "expression": {"type": "str", "required": True, "label": "表达式"},
    "new_col": {"type": "str", "required": True, "label": "新列名"}
})
def execute_col_calc(df, params):
    expression = params["expression"]
    new_col = params["new_col"]
    df = df.copy()
    df[new_col] = df.eval(expression)
    return df


# ============================================================
# 行操作
# ============================================================

@register_node("row_dedup", {
    "columns": {"type": "list", "required": False, "label": "去重依据列"}
})
def execute_row_dedup(df, params):
    columns = params.get("columns")
    return df.drop_duplicates(subset=columns)


@register_node("row_sort", {
    "column": {"type": "str", "required": True, "label": "排序列"},
    "order": {"type": "str", "required": True, "label": "排序方式", "options": ["asc", "desc"]}
})
def execute_row_sort(df, params):
    column = params["column"]
    order = params["order"]
    if column not in df.columns:
        raise ValueError(f"列 '{column}' 不存在")
    return df.sort_values(by=column, ascending=(order == "asc"))


@register_node("row_fillna", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "method": {"type": "str", "required": True, "label": "填充方式", "options": ["value", "ffill", "bfill"]},
    "fill_value": {"type": "any", "required": False, "label": "填充值"}
})
def execute_row_fillna(df, params):
    column = params["column"]
    method = params["method"]
    fill_value = params.get("fill_value")
    if column not in df.columns:
        raise ValueError(f"列 '{column}' 不存在")
    df = df.copy()
    if method == "value":
        if fill_value is None:
            raise ValueError("使用 value 方式填充时必须提供 fill_value")
        df[column] = df[column].fillna(fill_value)
    elif method == "ffill":
        df[column] = df[column].ffill()
    elif method == "bfill":
        df[column] = df[column].bfill()
    else:
        raise ValueError(f"不支持的填充方式: '{method}'，可选: value/ffill/bfill")
    return df


# ============================================================
# 高级操作
# ============================================================

@register_node("group_agg", {
    "group_cols": {"type": "list", "required": True, "label": "分组列"},
    "agg_col": {"type": "str", "required": True, "label": "聚合列"},
    "func": {"type": "str", "required": True, "label": "聚合函数"}
})
def execute_group_agg(df, params):
    group_cols = params["group_cols"]
    agg_col = params["agg_col"]
    func = params["func"]
    for col in group_cols:
        if col not in df.columns:
            raise ValueError(f"列 '{col}' 不存在")
    if agg_col not in df.columns:
        raise ValueError(f"列 '{agg_col}' 不存在")

    result = df.groupby(group_cols)[agg_col].agg(func).reset_index()

    # 将聚合结果列重命名为「聚合函数名(列名)」格式
    _agg_labels = {
        "sum": "求和",
        "mean": "均值",
        "count": "计数",
        "max": "最大值",
        "min": "最小值",
    }
    agg_label = _agg_labels.get(func, func)
    if agg_col in result.columns:
        result = result.rename(columns={agg_col: f"{agg_label}({agg_col})"})

    return result


@register_node("pivot", {
    "index": {"type": "list", "required": True, "label": "行索引列（支持多选）"},
    "columns": {"type": "str", "required": False, "label": "列索引列"},
    "values": {"type": "str", "required": True, "label": "值列"},
    "aggfunc": {"type": "str", "required": True, "label": "聚合函数", "options": ["sum", "mean", "count", "max", "min"]}
})
def execute_pivot(df, params):
    # 兼容单值和多值：字符串自动转为列表
    index = params.get("index", [])
    if isinstance(index, str):
        index = [index] if index else []
    if not index:
        raise ValueError("缺少参数: 行索引列")

    columns = params.get("columns") or None
    values = params.get("values", "")
    aggfunc = params.get("aggfunc", "sum")

    if not values:
        raise ValueError("缺少参数: 值列")

    for idx_col in index:
        if idx_col not in df.columns:
            raise ValueError(f"行索引列 '{idx_col}' 不存在")
    if values not in df.columns:
        raise ValueError(f"值列 '{values}' 不存在")
    if columns and columns not in df.columns:
        raise ValueError(f"列索引列 '{columns}' 不存在")

    result = pd.pivot_table(
        df, index=index, columns=columns, values=values, aggfunc=aggfunc
    ).reset_index()

    # 将值列的标题重命名为「聚合函数名(列名)」格式，如 求和(金额)、计数(人员)
    _agg_labels = {
        "sum": "求和",
        "mean": "均值",
        "count": "计数",
        "max": "最大值",
        "min": "最小值",
    }
    agg_label = _agg_labels.get(aggfunc, aggfunc)

    index_set = set(index)
    new_columns = {}
    for col in result.columns:
        if col in index_set:
            continue
        if isinstance(col, tuple):
            # 有列索引时，pivot_table 产出多级列名: (值列名, 列值)
            new_name = f"{agg_label}({col[0]})_{col[1]}"
        else:
            # 无列索引时，单级列名就是值列名本身
            new_name = f"{agg_label}({col})"
        new_columns[col] = new_name

    if new_columns:
        result = result.rename(columns=new_columns)

    return result


@register_node("type_convert", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "target_type": {"type": "str", "required": True, "label": "目标类型", "options": ["int", "float", "str", "datetime"]}
})
def execute_type_convert(df, params):
    column = params["column"]
    target_type = params["target_type"]
    if column not in df.columns:
        raise ValueError(f"列 '{column}' 不存在")
    df = df.copy()
    try:
        if target_type == "int":
            df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int64")
        elif target_type == "float":
            df[column] = pd.to_numeric(df[column], errors="coerce")
        elif target_type == "str":
            df[column] = df[column].astype(str)
        elif target_type == "datetime":
            df[column] = pd.to_datetime(df[column], errors="coerce")
        else:
            raise ValueError(f"不支持的目标类型: '{target_type}'，可选: int/float/str/datetime")
    except Exception as e:
        raise ValueError(f"类型转换失败（{column} -> {target_type}）: {e}")
    return df


@register_node("cond_assign", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "condition": {"type": "str", "required": True, "label": "条件表达式"},
    "true_val": {"type": "str_or_num", "required": True, "label": "条件为真的值"},
    "false_val": {"type": "str_or_num", "required": True, "label": "条件为假的值"},
    "new_col": {"type": "str", "required": False, "label": "新列名"}
})
def execute_cond_assign(df, params):
    column = params["column"]
    condition = params["condition"]
    true_val = params["true_val"]
    false_val = params["false_val"]
    new_col = params.get("new_col") or column
    if column not in df.columns:
        raise ValueError(f"列 '{column}' 不存在")
    df = df.copy()
    mask = df.eval(condition)
    df[new_col] = np.where(mask, true_val, false_val)
    return df


# ============================================================
# 辅助函数
# ============================================================

_NODE_META = {
    "text_filter":   {"category": "文本操作", "label": "文本筛选"},
    "text_replace":  {"category": "文本操作", "label": "文本替换"},
    "text_slice":    {"category": "文本操作", "label": "文本截取"},
    "text_trim":     {"category": "文本操作", "label": "去除空格"},
    "text_case":     {"category": "文本操作", "label": "大小写转换"},
    "regex_extract": {"category": "文本操作", "label": "正则提取"},
    "num_filter":    {"category": "数值操作", "label": "数值筛选"},
    "num_arithmetic":{"category": "数值操作", "label": "四则运算"},
    "num_round":     {"category": "数值操作", "label": "数值取整"},
    "num_aggregate": {"category": "数值操作", "label": "聚合计算"},
    "date_format":   {"category": "日期操作", "label": "日期格式化"},
    "date_extract":  {"category": "日期操作", "label": "日期提取"},
    "date_filter":   {"category": "日期操作", "label": "日期筛选"},
    "col_delete":    {"category": "列操作",   "label": "删除列"},
    "col_rename":    {"category": "列操作",   "label": "重命名列"},
    "col_split":     {"category": "列操作",   "label": "拆分列"},
    "col_merge":     {"category": "列操作",   "label": "合并列"},
    "col_calc":      {"category": "列操作",   "label": "跨列计算"},
    "row_dedup":     {"category": "行操作",   "label": "去重"},
    "row_sort":      {"category": "行操作",   "label": "排序"},
    "row_fillna":    {"category": "行操作",   "label": "空值填充"},
    "group_agg":     {"category": "高级操作", "label": "分组聚合"},
    "pivot":         {"category": "高级操作", "label": "透视表"},
    "vlookup":       {"category": "高级操作", "label": "跨表查找"},
    "custom_expr":   {"category": "高级操作", "label": "自定义表达式"},
    "type_convert":  {"category": "高级操作", "label": "类型转换"},
    "cond_assign":   {"category": "高级操作", "label": "条件赋值"},
}


def get_node_types_info():
    """返回所有节点类型的信息（供 /node-types API 使用）"""
    result = {}
    for node_type, info in NODE_REGISTRY.items():
        meta = _NODE_META.get(node_type, {"category": "未分类", "label": node_type})
        result[node_type] = {
            "type": node_type,
            "category": meta["category"],
            "label": meta["label"],
            "params_schema": info["params_schema"],
        }
    return result
