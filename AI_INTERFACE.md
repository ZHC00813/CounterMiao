# AI外置智能包接口

先运行桌面程序，在AI/API面板启动接口。默认URL为`http://127.0.0.1:8765`。复制本机访问令牌；需要修改时打开“允许外部AI修改”。不要将真实令牌、API Key或真实批次提交到Git。

## HTTP

所有请求使用 `Authorization: Bearer <本机令牌>`。

- `GET /v1/state`：当前批次、项目、报销项和发票元数据，不返回AI Key。
- `GET /v1/schema`：类型、操作列表和当前写权限。
- `POST /v1/actions`：执行一项结构化操作，默认只读时返回403。

示例（ID须先从state读取）：

```json
{"op":"create_project","name":"设备采购报销","kind":"物资采购"}
{"op":"create_entry","project_id":"上一步返回的项目ID","name":"传感器采购"}
```

支持操作：`create_project`、`rename_project`、`delete_project`、`restore`、`create_entry`、`rename_entry`、`delete_entry`、`set_flag`、`mark_complete`、`check`、`export`、`attach`、`move_invoice`。

- 修改名称：`project_id`、可选`entry_id`、`name`。
- 标红/隐藏：`set_flag`加`flag: red|hidden`和`value: true|false`。
- 删除：对应项目/报销项ID；仅进入回收站，不删除原件。
- 恢复：`restore`加`record_id`；子项恢复前父项目需存在。
- 附件：`attach`加项目、报销项ID、合法`label`及本机`paths`数组。签字件在界面按每份验收单关联。
- 移票：`move_invoice`加项目、源报销项ID、`target_entry_id`及`invoice_number`，之后重新检查规则和签字件。
- 检查：`check`加`project_id`。
- 导出：`export`加`project_id`、已存在的`output_dir`。

程序不开放任意代码执行或直接修改发票金额；不接受网页Origin来源，不对局域网提供服务。操作写入本机日志。默认关闭，退出程序时停止。

## MCP客户端配置

接口工具是独立的`CounterMiaoMCP.exe`，以stdio交换逐行JSON-RPC。先在桌面程序开启HTTP接口，再配置支持MCP的客户端。

```json
{
  "mcpServers": {
    "reimbursement": {
      "command": "C:\\你的解压目录\\CounterMiao\\CounterMiaoMCP.exe",
      "env": {
        "REIMBURSE_URL": "http://127.0.0.1:8765",
        "REIMBURSE_TOKEN": "从程序中复制的本机令牌"
      }
    }
  }
}
```

各客户端配置文件结构可能不同，填写同一个command和env即可；没有替用户修改Codex/Claude客户端设置。工具名为`reimbursement_state`与`reimbursement_action`。仅测试标准握手、工具清单及本机请求，没有逐一验证每个第三方客户端版本。

## 内置模型

Base URL、模型ID和Key由用户配置。OpenAI/DeepSeek/Kimi走Chat Completions格式；Claude走Messages格式。Key使用Windows当前用户DPAPI保存。向外部模型发送项目信息前提示接收地址；返回计划需查看后执行。真实服务账户联通及费用未做验证。

4.1：create_project 必须提供有效 kind；create_entry 继承所属报销项类型，可省略 kind，显式提供不同类型会被拒绝。旧版混合类型报销项不强制改写。
