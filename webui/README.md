# webui（系统看板 · 官方插件）

## 能力定位
**系统看板**：一个收束页，把全系统能力变成目录——插件（启用/停用/卸载）、蓝图下的 API（契约+信息+调试）、以及可嵌套分组的动态收藏夹（360 收藏夹式）。解决"系统有什么能力、入口在哪、怎么管理插件、怎么试 API"的发现/管理/导航问题。

**数据源 = 公开 API**：看板是纯静态单页，浏览器直接采集 `/Documentation/*`、`/Workspace/*`（与 Agent 同一视角、统一信封），本插件的 Python 只负责出页面 + 收藏夹 CRUD + 用 V2 信息型校验器让 API 自证信息。**不读 System 内部结构。**

## 页面与约定
- 入口：`GET /webui/home`（浏览器打开；页面型，POST 拒绝）
- **URL 拼法（名字合一）**：`/蓝图名/函数名`；**蓝图禁写根路由**；路径 = 函数名
- **类型自证（不靠命名/硬编码）**：展开函数时 GET 一次按响应分流——`text/html` = 页面（前往/收藏）；`application/json` = API（契约 + 信息保留键）
- **信息保留键**（V2 信息型校验器）：GET 契约附带 `蓝图信息` / `api信息` / `自定义信息`（均为 dict），webui/Agent 据此渲染详情
- **收藏规则**：只能从蓝图区（页面展开后）收藏进组；管理/移除在"管理收藏夹"里；支持组嵌套

## 布局（看板信息架构）
- 顶部**收藏栏**：所有收藏组横向摊开（下拉），+组/管理收藏夹
- **🧩 插件 tab**：蓝图名 + 状态 + 启用/停用/卸载（**仅 Workspace 管理的外部插件**有真按钮；官方插件 = init 装配，无运行期启停）
- **🔌 API 列表 tab**：横向蓝图子Tab → 蓝图信息（V2 采收）+ 该蓝图函数折叠

## API（本插件，统一信封 {"result": ...} / {"error": ...}）

| 方法 | 路径 | 参数 | 说明 |
|---|---|---|---|
| GET | `/webui/home` | — | 看板页（HTML） |
| POST/GET | `/webui/favorites` | — | 查看收藏夹整棵组树（V2 信息型） |
| POST/GET | `/webui/group_add` | `name`, `parent_id`(可空) | 新增组（空=顶层） |
| POST/GET | `/webui/group_rename` | `id`, `name` | 重命名组 |
| POST/GET | `/webui/group_remove` | `id` | 删除组（递归含子组条目） |
| POST/GET | `/webui/item_add` | `group_id`, `bp`, `fn`, `url`, `is_page` | 收藏条目 |
| POST/GET | `/webui/item_remove` | `group_id`, `url` | 移除条目 |

收藏数据持久化在插件包内 `webui.json`（运行时数据，不入库；嵌套组结构 `{id,name,groups,items}`）。

## 装配方式
官方插件（属于 AssistantSay-FunctionTools 仓库）。按仓库根 README 流程：把本文件夹内容放进 `SERVE/FunctionTools/webui/`（webui.py + static/），在 `SERVE/FunctionTools/__init__.py` 登记一行：

```python
from .webui import WEBUI
```

**前置依赖**：需先装配校验库分支 `AssistantSay_HANDLER_V2`（VL 仓库 → `SERVE/VerificationLibrary/AssistantSay_HANDLER_V2/`，禁止急切再导出，由本插件显式引入）。

然后 `POST /overload?reason=装配了webui看板`，浏览器打开 `/webui/home`。

## 边界与红线
- 看板数据全部走公开 API；页面/静态资源在本插件包内（static/ 绝对路径定位）
- 页面首页 home 当前用基座派生就地 `Page` 子类（页面语义原型）；API 用 V2 信息型；页面语义稳定后统一收编 VL 页面分支
- 插件开发范式与红线见 AssistantSay-FunctionTools 仓库根 README

## 依赖声明
- 校验库版本：基座 `FunctionHandler`（页面 home 的就地 Page 子类，原型期）
- 校验库版本：`AssistantSay_HANDLER_V2`（收藏/API 用 V2 信息型，随 GET 自证 蓝图信息/api信息/自定义信息）
