from node_registry import NODE_REGISTRY


def execute_workflow(rows, nodes_chain, stop_on_error=False):
    """
    按顺序执行节点链

    Args:
        rows: 输入数据 list[dict]
        nodes_chain: 节点列表 [{"id": "...", "type": "...", "params": {...}}, ...]
        stop_on_error: 是否遇到错误时停止执行

    Returns:
        dict: {
            "result_rows": list[dict],
            "columns": list[str],
            "errors": [{"node_id": "...", "node_type": "...", "error": "..."}],
            "executed_count": int,
            "total_count": int
        }
    """
    result_rows = [{**r} for r in rows]
    errors = []
    executed_count = 0
    total_count = len(nodes_chain)

    for node in nodes_chain:
        node_id = node.get("id", "unknown")
        node_type = node.get("type", "")
        params = node.get("params", {})

        # 检查节点类型是否在注册表中
        if node_type not in NODE_REGISTRY:
            error_msg = f"未知的节点类型: '{node_type}'"
            errors.append({
                "node_id": node_id,
                "node_type": node_type,
                "error": error_msg,
            })
            if stop_on_error:
                break
            continue

        # 执行节点
        try:
            execute_func = NODE_REGISTRY[node_type]["execute"]
            result_rows = execute_func(result_rows, params)
            executed_count += 1
        except Exception as e:
            error_msg = str(e)
            errors.append({
                "node_id": node_id,
                "node_type": node_type,
                "error": error_msg,
            })
            if stop_on_error:
                break

    # 推断列名
    columns = list(result_rows[0].keys()) if result_rows else []

    return {
        "result_rows": result_rows,
        "columns": columns,
        "errors": errors,
        "executed_count": executed_count,
        "total_count": total_count,
    }
