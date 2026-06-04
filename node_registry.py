"""
数据处理节点注册表 — 纯 Python 实现（无 pandas/numpy 依赖）
所有节点函数接受 list[dict] 作为数据输入，返回 list[dict]
"""
import re
import math
from datetime import datetime, date

NODE_REGISTRY = {}  # {node_type: {"execute": func, "params_schema": {...}}}

# ---- 日期解析工具 ----

_DATE_FORMATS = [
    '%Y/%m/%d %H:%M:%S',
    '%Y-%m-%d %H:%M:%S',
    '%Y/%m/%d',
    '%Y-%m-%d',
    '%Y%m%d',
    '%d/%m/%Y',
]


def _parse_datetime_val(val):
    """解析单个值为 datetime，失败返回 None"""
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val if isinstance(val, datetime) else datetime.combine(val, datetime.min.time())
    s = str(val).strip()
    if not s:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _to_float(val):
    """安全转为 float，失败返回 None"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        if isinstance(val, float) and math.isnan(val):
            return None
        return float(val)
    try:
        return float(str(val).strip().replace(',', ''))
    except (ValueError, TypeError):
        return None


def _to_int(val):
    """安全转为 int，失败返回 None"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        if isinstance(val, float) and math.isnan(val):
            return None
        return int(val)
    try:
        return int(float(str(val).strip().replace(',', '')))
    except (ValueError, TypeError):
        return None


def _is_nan(val):
    """检查值是否为 NaN/None/空"""
    if val is None:
        return True
    if isinstance(val, float) and math.isnan(val):
        return True
    return False


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
def execute_text_filter(rows, params):
    column = params["column"]
    keyword = params["keyword"].lower()
    if rows and column not in rows[0]:
        raise ValueError(f"列 '{column}' 不存在")
    return [r for r in rows if keyword in str(r.get(column, '')).lower()]


@register_node("text_replace", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "old": {"type": "str", "required": True, "label": "原文本"},
    "new": {"type": "str", "required": True, "label": "新文本"}
})
def execute_text_replace(rows, params):
    column = params["column"]
    old = params["old"]
    new = params["new"]
    if rows and column not in rows[0]:
        raise ValueError(f"列 '{column}' 不存在")
    return [{**r, column: str(r.get(column, '')).replace(old, new)} for r in rows]


@register_node("text_slice", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "start": {"type": "int", "required": True, "label": "起始位置"},
    "end": {"type": "int", "required": True, "label": "结束位置"}
})
def execute_text_slice(rows, params):
    column = params["column"]
    start = params["start"]
    end = params["end"]
    if rows and column not in rows[0]:
        raise ValueError(f"列 '{column}' 不存在")
    return [{**r, column: str(r.get(column, ''))[start:end]} for r in rows]


@register_node("text_trim", {
    "column": {"type": "str", "required": True, "label": "列名"}
})
def execute_text_trim(rows, params):
    column = params["column"]
    if rows and column not in rows[0]:
        raise ValueError(f"列 '{column}' 不存在")
    return [{**r, column: str(r.get(column, '')).strip()} for r in rows]


@register_node("text_case", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "mode": {"type": "str", "required": True, "label": "转换模式", "options": ["upper", "lower", "title"]}
})
def execute_text_case(rows, params):
    column = params["column"]
    mode = params["mode"]
    if rows and column not in rows[0]:
        raise ValueError(f"列 '{column}' 不存在")
    if mode == "upper":
        return [{**r, column: str(r.get(column, '')).upper()} for r in rows]
    elif mode == "lower":
        return [{**r, column: str(r.get(column, '')).lower()} for r in rows]
    elif mode == "title":
        return [{**r, column: str(r.get(column, '')).title()} for r in rows]
    else:
        raise ValueError(f"不支持的大小写模式: '{mode}'，可选: upper/lower/title")


@register_node("regex_extract", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "pattern": {"type": "str", "required": True, "label": "正则表达式"},
    "new_col": {"type": "str", "required": False, "label": "新列名"}
})
def execute_regex_extract(rows, params):
    column = params["column"]
    pattern = params["pattern"]
    new_col = params.get("new_col") or column + "_extracted"
    if rows and column not in rows[0]:
        raise ValueError(f"列 '{column}' 不存在")
    compiled = re.compile(pattern)
    result = []
    for r in rows:
        m = compiled.search(str(r.get(column, '')))
        result.append({**r, new_col: m.group(1) if m and m.groups() else (m.group(0) if m else '')})
    return result


# ============================================================
# 数值类操作
# ============================================================

@register_node("num_filter", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "operator": {"type": "str", "required": True, "label": "运算符", "options": [">", "<", "=", ">=", "<=", "!="]},
    "value": {"type": "float", "required": True, "label": "数值"}
})
def execute_num_filter(rows, params):
    column = params["column"]
    operator = params["operator"]
    value = params["value"]
    if rows and column not in rows[0]:
        raise ValueError(f"列 '{column}' 不存在")

    ops = {
        ">": lambda a, b: (a is not None) and a > b,
        "<": lambda a, b: (a is not None) and a < b,
        "=": lambda a, b: (a is not None) and a == b,
        ">=": lambda a, b: (a is not None) and a >= b,
        "<=": lambda a, b: (a is not None) and a <= b,
        "!=": lambda a, b: (a is not None) and a != b,
    }
    if operator not in ops:
        raise ValueError(f"不支持的运算符: '{operator}'，可选: >/</=/>=/<=/!=")

    compare = ops[operator]
    return [r for r in rows if compare(_to_float(r.get(column)), value)]


@register_node("num_arithmetic", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "operator": {"type": "str", "required": True, "label": "运算符", "options": ["+", "-", "*", "÷"]},
    "value": {"type": "float", "required": True, "label": "数值"}
})
def execute_num_arithmetic(rows, params):
    column = params["column"]
    operator = params["operator"]
    value = params["value"]
    if rows and column not in rows[0]:
        raise ValueError(f"列 '{column}' 不存在")

    result = []
    for r in rows:
        num = _to_float(r.get(column))
        if num is None:
            result.append({**r})
            continue
        if operator == "+":
            new_val = num + value
        elif operator == "-":
            new_val = num - value
        elif operator == "*":
            new_val = num * value
        elif operator == "÷":
            if value == 0:
                raise ValueError("除数不能为 0")
            new_val = num / value
        else:
            raise ValueError(f"不支持的运算符: '{operator}'，可选: +/-/*/÷")
        result.append({**r, column: new_val})
    return result


@register_node("num_round", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "decimals": {"type": "int", "required": True, "label": "小数位数"}
})
def execute_num_round(rows, params):
    column = params["column"]
    decimals = params["decimals"]
    if rows and column not in rows[0]:
        raise ValueError(f"列 '{column}' 不存在")
    return [{**r, column: round(_to_float(r.get(column)) or 0, decimals)} for r in rows]


@register_node("num_aggregate", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "func": {"type": "str", "required": True, "label": "聚合函数", "options": ["sum", "avg", "max", "min", "count"]}
})
def execute_num_aggregate(rows, params):
    column = params["column"]
    func = params["func"]
    if rows and column not in rows[0]:
        raise ValueError(f"列 '{column}' 不存在")

    nums = [_to_float(r.get(column)) for r in rows]
    nums = [n for n in nums if n is not None]

    if func == "sum":
        result_val = sum(nums) if nums else 0
    elif func == "avg":
        result_val = sum(nums) / len(nums) if nums else 0
    elif func == "max":
        result_val = max(nums) if nums else None
    elif func == "min":
        result_val = min(nums) if nums else None
    elif func == "count":
        result_val = len(nums)
    else:
        raise ValueError(f"不支持的聚合函数: '{func}'，可选: sum/avg/max/min/count")

    result = [{**r} for r in rows]
    if result:
        if "_aggregate" not in result[0]:
            result[0]["_aggregate"] = {}
        result[0]["_aggregate"][f"{func}_{column}"] = result_val
    return result


# ============================================================
# 日期类操作
# ============================================================

@register_node("date_format", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "format": {"type": "str", "required": True, "label": "格式字符串"}
})
def execute_date_format(rows, params):
    column = params["column"]
    fmt = params["format"]
    if rows and column not in rows[0]:
        raise ValueError(f"列 '{column}' 不存在")
    result = []
    for r in rows:
        dt = _parse_datetime_val(r.get(column))
        formatted = dt.strftime(fmt) if dt else str(r.get(column, ''))
        result.append({**r, column: formatted})
    return result


@register_node("date_extract", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "part": {"type": "str", "required": True, "label": "提取部分", "options": ["year", "month", "day", "weekday"]},
    "new_col": {"type": "str", "required": False, "label": "新列名"}
})
def execute_date_extract(rows, params):
    column = params["column"]
    part = params["part"]
    new_col = params.get("new_col") or column + "_" + part
    if rows and column not in rows[0]:
        raise ValueError(f"列 '{column}' 不存在")

    extract_map = {
        "year": lambda d: d.year,
        "month": lambda d: d.month,
        "day": lambda d: d.day,
        "weekday": lambda d: d.weekday(),
    }
    if part not in extract_map:
        raise ValueError(f"不支持的日期部分: '{part}'，可选: year/month/day/weekday")

    extract = extract_map[part]
    result = []
    for r in rows:
        dt = _parse_datetime_val(r.get(column))
        result.append({**r, new_col: extract(dt) if dt else None})
    return result


@register_node("date_filter", {
    "column": {"type": "str", "required": True, "label": "日期列"},
    "operator": {"type": "str", "required": True, "label": "筛选方式", "options": ["大于", "小于", "等于", "日期范围内"]},
    "date1": {"type": "str", "required": True, "label": "日期"},
    "date2": {"type": "str", "required": False, "label": "结束日期（between时）"},
})
def execute_date_filter(rows, params):
    column = params["column"]
    operator = params["operator"]
    date1_str = params["date1"]
    date2_str = params.get("date2", "")
    if rows and column not in rows[0]:
        raise ValueError(f"列 '{column}' 不存在")

    d1 = _parse_datetime_val(date1_str)
    if d1 is None:
        raise ValueError(f"无法解析日期: {date1_str}")

    d2 = None
    if date2_str:
        d2 = _parse_datetime_val(date2_str)
        if d2 is None:
            raise ValueError(f"无法解析日期: {date2_str}")

    result = []
    for r in rows:
        dt = _parse_datetime_val(r.get(column))
        if dt is None:
            continue

        if operator in ("大于", "gt"):
            if dt > d1:
                result.append(r)
        elif operator in ("小于", "lt"):
            if dt < d1:
                result.append(r)
        elif operator in ("等于", "eq"):
            if dt.date() == d1.date():
                result.append(r)
        elif operator in ("日期范围内", "between"):
            if d2 is None:
                raise ValueError("between 模式需要提供结束日期")
            if d1 <= dt <= d2:
                result.append(r)
        else:
            raise ValueError(f"不支持的筛选方式: '{operator}'")

    return result


# ============================================================
# 列操作
# ============================================================

@register_node("col_delete", {
    "column": {"type": "str_or_list", "required": True, "label": "列名"}
})
def execute_col_delete(rows, params):
    column = params["column"]
    if isinstance(column, str):
        cols_to_drop = {column}
    else:
        cols_to_drop = set(column)
    if rows:
        for col in cols_to_drop:
            if col not in rows[0]:
                raise ValueError(f"列 '{col}' 不存在")
    return [{k: v for k, v in r.items() if k not in cols_to_drop} for r in rows]


@register_node("col_select", {
    "columns": {"type": "list", "required": True, "label": "要保留的列"}
})
def execute_col_select(rows, params):
    columns = params["columns"]
    if isinstance(columns, str):
        columns = [columns]
    if not columns:
        raise ValueError("请至少选择一列")
    if rows:
        for col in columns:
            if col not in rows[0]:
                raise ValueError(f"列 '{col}' 不存在")
    return [{col: r.get(col) for col in columns} for r in rows]


@register_node("col_rename", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "new_name": {"type": "str", "required": True, "label": "新列名"}
})
def execute_col_rename(rows, params):
    column = params["column"]
    new_name = params["new_name"]
    if rows and column not in rows[0]:
        raise ValueError(f"列 '{column}' 不存在")
    result = []
    for r in rows:
        new_r = {}
        for k, v in r.items():
            new_r[new_name if k == column else k] = v
        result.append(new_r)
    return result


@register_node("col_split", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "delimiter": {"type": "str", "required": True, "label": "分隔符"},
    "new_cols": {"type": "list", "required": False, "label": "新列名列表"}
})
def execute_col_split(rows, params):
    column = params["column"]
    delimiter = params["delimiter"]
    new_cols = params.get("new_cols")
    if rows and column not in rows[0]:
        raise ValueError(f"列 '{column}' 不存在")

    result = []
    for r in rows:
        parts = str(r.get(column, '')).split(delimiter)
        new_r = dict(r)
        if new_cols:
            for i, name in enumerate(new_cols):
                new_r[name] = parts[i] if i < len(parts) else None
        else:
            for i, part in enumerate(parts):
                new_r[f"{column}_{i+1}"] = part
        result.append(new_r)
    return result


@register_node("col_merge", {
    "columns": {"type": "list", "required": True, "label": "列名列表"},
    "delimiter": {"type": "str", "required": True, "label": "分隔符"},
    "new_col": {"type": "str", "required": True, "label": "新列名"}
})
def execute_col_merge(rows, params):
    columns = params["columns"]
    delimiter = params["delimiter"]
    new_col = params["new_col"]
    if rows:
        for col in columns:
            if col not in rows[0]:
                raise ValueError(f"列 '{col}' 不存在")
    result = []
    for r in rows:
        parts = [str(r.get(col, '')) for col in columns]
        result.append({**r, new_col: delimiter.join(parts)})
    return result


@register_node("col_calc", {
    "expression": {"type": "str", "required": True, "label": "表达式"},
    "new_col": {"type": "str", "required": True, "label": "新列名"}
})
def execute_col_calc(rows, params):
    expression = params["expression"]
    new_col = params["new_col"]
    result = []
    for r in rows:
        safe_vals = {}
        for k, v in r.items():
            safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', str(k))
            nv = _to_float(v)
            safe_vals[safe_name] = nv if nv is not None else 0

        expr = expression
        for k in r.keys():
            safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', str(k))
            if k != safe_name:
                expr = expr.replace(k, safe_name)

        try:
            calc_val = eval(expr, {"__builtins__": {}}, safe_vals)
        except Exception:
            calc_val = None
        result.append({**r, new_col: calc_val})
    return result


# ============================================================
# 行操作
# ============================================================

@register_node("row_dedup", {
    "columns": {"type": "list", "required": False, "label": "去重依据列"}
})
def execute_row_dedup(rows, params):
    columns = params.get("columns")
    if not columns:
        seen = set()
        result = []
        for r in rows:
            key = tuple(str(r.get(k, '')) for k in sorted(r.keys()))
            if key not in seen:
                seen.add(key)
                result.append(r)
        return result
    else:
        if isinstance(columns, str):
            columns = [columns]
        seen = set()
        result = []
        for r in rows:
            key = tuple(str(r.get(c, '')) for c in columns)
            if key not in seen:
                seen.add(key)
                result.append(r)
        return result


@register_node("row_sort", {
    "column": {"type": "str", "required": True, "label": "排序列"},
    "order": {"type": "str", "required": True, "label": "排序方式", "options": ["asc", "desc"]}
})
def execute_row_sort(rows, params):
    column = params["column"]
    order = params["order"]
    if rows and column not in rows[0]:
        raise ValueError(f"列 '{column}' 不存在")
    reverse = (order == "desc")

    # 分离空值和非空值，空值始终排在末尾（与 pandas 默认 na_position='last' 一致）
    valid_rows = []
    na_rows = []
    for r in rows:
        v = r.get(column)
        if _is_nan(v):
            na_rows.append(r)
        else:
            valid_rows.append(r)

    def sort_key(r):
        v = r.get(column)
        f = _to_float(v)
        if f is not None:
            return (0, f, '')
        return (1, 0, str(v or ''))

    valid_rows.sort(key=sort_key, reverse=reverse)
    return valid_rows + na_rows


@register_node("row_fillna", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "method": {"type": "str", "required": True, "label": "填充方式", "options": ["value", "ffill", "bfill"]},
    "fill_value": {"type": "any", "required": False, "label": "填充值"}
})
def execute_row_fillna(rows, params):
    column = params["column"]
    method = params["method"]
    fill_value = params.get("fill_value")
    if rows and column not in rows[0]:
        raise ValueError(f"列 '{column}' 不存在")

    if method == "value":
        if fill_value is None:
            raise ValueError("使用 value 方式填充时必须提供 fill_value")
        return [{**r, column: fill_value if _is_nan(r.get(column)) else r[column]} for r in rows]

    elif method == "ffill":
        result = []
        last_valid = None
        for r in rows:
            v = r.get(column)
            if _is_nan(v):
                result.append({**r, column: last_valid})
            else:
                last_valid = v
                result.append(dict(r))
        return result

    elif method == "bfill":
        result = [dict(r) for r in rows]
        next_valid = None
        for i in range(len(result) - 1, -1, -1):
            v = result[i].get(column)
            if _is_nan(v):
                result[i][column] = next_valid
            else:
                next_valid = v
        return result

    else:
        raise ValueError(f"不支持的填充方式: '{method}'，可选: value/ffill/bfill")


# ============================================================
# 高级操作
# ============================================================

@register_node("group_agg", {
    "group_cols": {"type": "list", "required": True, "label": "分组列"},
    "agg_col": {"type": "str", "required": True, "label": "聚合列"},
    "func": {"type": "str", "required": True, "label": "聚合函数"}
})
def execute_group_agg(rows, params):
    group_cols = params["group_cols"]
    agg_col = params["agg_col"]
    func = params["func"]
    if isinstance(group_cols, str):
        group_cols = [group_cols]
    if rows:
        for col in group_cols:
            if col not in rows[0]:
                raise ValueError(f"列 '{col}' 不存在")
        if agg_col not in rows[0]:
            raise ValueError(f"列 '{agg_col}' 不存在")

    groups = {}
    for r in rows:
        key = tuple(str(r.get(c, '')) for c in group_cols)
        if key not in groups:
            groups[key] = []
        groups[key].append(r)

    _agg_labels = {
        "sum": "求和",
        "mean": "均值",
        "count": "计数",
        "max": "最大值",
        "min": "最小值",
    }
    agg_label = _agg_labels.get(func, func)
    result_col_name = f"{agg_label}({agg_col})"

    result = []
    for key, group_rows in groups.items():
        vals = [_to_float(r.get(agg_col)) for r in group_rows]
        vals = [v for v in vals if v is not None]

        if func == "sum":
            agg_val = sum(vals) if vals else 0
        elif func == "mean":
            agg_val = sum(vals) / len(vals) if vals else 0
        elif func == "count":
            agg_val = len(vals)
        elif func == "max":
            agg_val = max(vals) if vals else None
        elif func == "min":
            agg_val = min(vals) if vals else None
        else:
            raise ValueError(f"不支持的聚合函数: '{func}'，可选: sum/mean/count/max/min")

        row = {col: (str(key[i]) if i < len(key) else '') for i, col in enumerate(group_cols)}
        row[result_col_name] = agg_val
        result.append(row)

    return result


@register_node("pivot", {
    "index": {"type": "list", "required": True, "label": "行索引列（支持多选）"},
    "columns": {"type": "str", "required": False, "label": "列索引列"},
    "values": {"type": "str", "required": True, "label": "值列"},
    "aggfunc": {"type": "str", "required": True, "label": "聚合函数", "options": ["sum", "mean", "count", "max", "min"]}
})
def execute_pivot(rows, params):
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

    if rows:
        for idx_col in index:
            if idx_col not in rows[0]:
                raise ValueError(f"行索引列 '{idx_col}' 不存在")
        if values not in rows[0]:
            raise ValueError(f"值列 '{values}' 不存在")
        if columns and columns not in rows[0]:
            raise ValueError(f"列索引列 '{columns}' 不存在")

    _agg_labels = {
        "sum": "求和",
        "mean": "均值",
        "count": "计数",
        "max": "最大值",
        "min": "最小值",
    }
    agg_label = _agg_labels.get(aggfunc, aggfunc)

    if columns:
        pivot_data = {}
        for r in rows:
            row_key = tuple(str(r.get(c, '')) for c in index)
            col_key = str(r.get(columns, ''))
            val = _to_float(r.get(values))
            if val is None:
                continue
            if row_key not in pivot_data:
                pivot_data[row_key] = {}
            if col_key not in pivot_data[row_key]:
                pivot_data[row_key][col_key] = []
            pivot_data[row_key][col_key].append(val)

        result = []
        for row_key, col_vals in pivot_data.items():
            row = {col: (str(row_key[i]) if i < len(row_key) else '') for i, col in enumerate(index)}
            for col_key, vals in col_vals.items():
                new_col = f"{agg_label}({values})_{col_key}"
                if aggfunc == "sum":
                    row[new_col] = sum(vals)
                elif aggfunc == "mean":
                    row[new_col] = sum(vals) / len(vals)
                elif aggfunc == "count":
                    row[new_col] = len(vals)
                elif aggfunc == "max":
                    row[new_col] = max(vals)
                elif aggfunc == "min":
                    row[new_col] = min(vals)
            result.append(row)
    else:
        pivot_data = {}
        for r in rows:
            row_key = tuple(str(r.get(c, '')) for c in index)
            val = _to_float(r.get(values))
            if val is None:
                continue
            if row_key not in pivot_data:
                pivot_data[row_key] = []
            pivot_data[row_key].append(val)

        new_col = f"{agg_label}({values})"
        result = []
        for row_key, vals in pivot_data.items():
            row = {col: (str(row_key[i]) if i < len(row_key) else '') for i, col in enumerate(index)}
            if aggfunc == "sum":
                row[new_col] = sum(vals)
            elif aggfunc == "mean":
                row[new_col] = sum(vals) / len(vals)
            elif aggfunc == "count":
                row[new_col] = len(vals)
            elif aggfunc == "max":
                row[new_col] = max(vals)
            elif aggfunc == "min":
                row[new_col] = min(vals)
            result.append(row)

    return result


@register_node("type_convert", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "target_type": {"type": "str", "required": True, "label": "目标类型", "options": ["int", "float", "str", "datetime"]}
})
def execute_type_convert(rows, params):
    column = params["column"]
    target_type = params["target_type"]
    if rows and column not in rows[0]:
        raise ValueError(f"列 '{column}' 不存在")

    result = []
    for r in rows:
        v = r.get(column)
        try:
            if target_type == "int":
                new_v = _to_int(v)
            elif target_type == "float":
                new_v = _to_float(v)
            elif target_type == "str":
                new_v = str(v) if v is not None else ''
            elif target_type == "datetime":
                new_v = _parse_datetime_val(v)
            else:
                raise ValueError(f"不支持的目标类型: '{target_type}'，可选: int/float/str/datetime")
        except Exception as e:
            raise ValueError(f"类型转换失败（{column} -> {target_type}）: {e}")
        result.append({**r, column: new_v})
    return result


@register_node("cond_assign", {
    "column": {"type": "str", "required": True, "label": "列名"},
    "condition": {"type": "str", "required": True, "label": "条件表达式"},
    "true_val": {"type": "str_or_num", "required": True, "label": "条件为真的值"},
    "false_val": {"type": "str_or_num", "required": True, "label": "条件为假的值"},
    "new_col": {"type": "str", "required": False, "label": "新列名"}
})
def execute_cond_assign(rows, params):
    column = params["column"]
    condition = params["condition"]
    true_val = params["true_val"]
    false_val = params["false_val"]
    new_col = params.get("new_col") or column
    if rows and column not in rows[0]:
        raise ValueError(f"列 '{column}' 不存在")

    result = []
    for r in rows:
        safe_vals = {}
        for k, v in r.items():
            safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', str(k))
            nv = _to_float(v)
            safe_vals[safe_name] = nv if nv is not None else 0

        expr = condition
        for k in r.keys():
            safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', str(k))
            if k != safe_name:
                expr = expr.replace(k, safe_name)

        try:
            cond_result = bool(eval(expr, {"__builtins__": {}}, safe_vals))
        except Exception:
            cond_result = False

        result.append({**r, new_col: true_val if cond_result else false_val})
    return result


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
    "col_select":    {"category": "列操作",   "label": "筛选列"},
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
