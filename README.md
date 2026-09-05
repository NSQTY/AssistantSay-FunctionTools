# AssistantSay-FunctionTools（官方仓库）

## 定位
AssistantSay 的官方插件库。定义插件开发规范，提供官方插件，是插件开发的唯一参考源。

开发完成的插件最终需装配进 **AssistantSay-SERVE** 才能运行。

**仓库形态**：本仓库是官方插件库容器——根 README（即本文档）是插件开发的唯一知识源；官方插件以**文件夹**为单位收录（一个插件 = 一个文件夹，含 `__init__.py` / `README.md` / 根目录蓝图模块），开发完成后按下方流程将插件文件夹 clone/copy 进 SERVE 挂点。

---

## ⚠️ 铁律：禁止修改 SERVE 代码

**任何组织、个人、Agent 均不能修改 AssistantSay-SERVE/ 下的任何代码。**

所有改动只能通过以下方式：clone/copy 插件 → 改 `__init__.py` 登记行 → `POST /overload`。

---

## 插件开发规范

### 1. 包结构契约
每个插件 = **一层包**，必须具备：
```
<插件名>/
├── <插件名>.py       根目录蓝图模块（module-level 建蓝图）
├── README.md         插件文档（必备）
└── (其它实现)        实现细节可任意嵌套
```

README.md 内容要求：**开头**必须有「能力定位：解决什么问题」一句；**末尾**必须有「## 依赖声明」节（见 §7）——一头一尾构成插件身份。

### 2. 名字合一原则
```
包名 = 蓝图名 = url_prefix
```

### 3. 蓝图与函数范式
```python
import System
from typing import Annotated

Tools = System.FlaskApp.AR.CBP.<插件名>.ModifyConfiguration(url_prefix='/<插件名>')

@Tools.route('/Do', methods=['POST', 'GET'])
@System.RouteInterception.CheckRequester()
def Do(param: Annotated[str, '参数说明']) -> Annotated[dict, '返回说明']:
    ...
```

### 4. 签名即契约
- 参数用 `Annotated[类型, '描述']`，契约在**装饰时**自动解析
- 路由名 == 函数名：`@route('/Do')` 配 `def Do`
- 必须套 `@CheckRequester()` 闸门
- **`return` 注解**：`Annotated` 的 return 会进契约（契约含 `return` 键，GET 契约可读到返回值说明）；裸 return 注解被跳过
- **裸字符串注解**（前向引用）会原样存入契约 type 字段，handler 拿到的是字符串而非类型

### 5. 依赖取用规范
```python
import System                      # 唯一导入
System.jsonify / System.request    # 第三方依赖从门面取
System.FlaskApp.AR
System.RouteInterception.CheckRequester
System.VerificationLibrary.FunctionHandler
```
**禁止**：直接 `from flask import ...` 或深路径 `from System.Core.X import ...`

### 6. ModifyConfiguration 注意事项
- 普通属性：同名即覆盖
- **callable 属性：禁止覆盖，抛 TypeError**（保护 Flask Blueprint 内置方法如 route、error_handler）
- 返回 self（链式调用）

### 7. 依赖声明（尾部强制）

每个插件 README.md 的**最末尾**必须有一节固定标题 `## 依赖声明`，注明本插件装配运行所需的校验库版本：

```
## 依赖声明
- 校验库版本：AssistantSay_HANDLER_V1    ← VL 仓库中的处理者文件夹名
- 或：校验库版本：基座                    ← 仅用默认 FunctionHandler，无分支依赖
```

规则：
- 依赖 = 插件代码中**显式引用**的 VL 处理者版本；未引用任何分支 → 写「基座」
- 声明的版本在 VL 仓库不存在或不完整 → 装配前必须先补齐对应 VL 内容，禁止跳过
- 声明与实现不符（如引用了 V2 却声明 V1）→ 契约违例
- 目的：插件包与对应校验库版本一一对应，杜绝装配错位

---

## 装配到 SERVE 的流程（分角色）

> 角色：**官方** = SERVE 仓库维护者（唯一有装配权）；**第三方开发者（含 Agent）** = clone 后自己开发插件的人，**禁止触碰 SERVE 任何文件**——连 `__init__` 都不能动、连 copy 进 SERVE 都不允许，只能经 Workspace API 外部化注册。消费者 = clone 后运行使用（只读/运行）。
> 装配动作分两类：**A. 官方装配**（官方插件 / 官方发布流程）与 **B. 第三方外部注册**（唯一通道 = Workspace API）。

### A. 官方装配（仅官方 / 官方发布流程；消费者执行官方给出的安装步骤不算私自修改）

把官方插件（本仓库内的 Workspace / webui 等）放入 SERVE：

**方式 1：clone（先克隆整个仓库，再复制插件文件夹——git 不能直接 clone 仓库内的子目录）**
```bash
cd your_path/AssistantSay-SERVE/FunctionTools
git clone https://github.com/NSQTY/AssistantSay-FunctionTools.git 临时目录
cp -r 临时目录/<插件名> .
rm -rf 临时目录
```

**方式 2：sparse checkout（只拉取目标插件文件夹，省流量）**
```bash
cd your_path/AssistantSay-SERVE/FunctionTools
git clone --depth 1 --filter=blob:none --sparse https://github.com/NSQTY/AssistantSay-FunctionTools.git 临时目录
git -C 临时目录 sparse-checkout set <插件名>
cp -r 临时目录/<插件名> .
rm -rf 临时目录
```

**方式 3：复制本地开发目录**
```bash
cp -r your_path/AssistantSay-FunctionTools/<插件名> your_path/AssistantSay-SERVE/FunctionTools/
```

**装配后必须两步（官方动作）**：
1. **登记**：在 `SERVE/FunctionTools/__init__.py` 加一行，把插件的蓝图导出来（以各插件 README 为准）：
   ```python
   from .<插件名> import <导出>      # 例: Workspace → from .Workspace import Registration; webui → from .webui import WEBUI
   ```
2. **重载**：`POST /overload?reason=登记了新插件<插件名>`

> ⚠️ 官方装配也禁止修改 `__init__.py` 以外的任何文件、禁止在 SERVE 内部创建其它文件。

### B. 第三方外部注册（唯一通道：Workspace API）

第三方插件 = **Python 包**（留在自己的目录，绝不放进 SERVE），经 Workspace 插件 API 登记：

1. 包契约必备：`README.md` + `requirements.txt`（依赖声明，无依赖可为空）+ `__init__.py`（包身份证）+ `main.py`（蓝图入口，**固定名**）；子包/子模块/资源任意，`main.py` 内相对导入
2. `POST /Workspace/RegistrationWorks` `{WorksPath}`（**入口固定 main.py，无需指定模块**）→ 包式预注册导入测试 + 蓝图重名检查 → 通过才写注册表
3. `POST /overload?reason=登记了插件X` → 启动时自动装配生效
4. 启停：`POST /Workspace/WorksStatus`；卸载：`POST /Workspace/RemoveWorks`（卸载后需重新登记才恢复）

> 🔴 **第三方红线**：禁止 copy/clone 插件进 SERVE、禁止改 `FunctionTools/__init__.py`、禁止在 SERVE 内创建任何文件——一切只经 Workspace API。

---

## 能力复用与禁止重叠（API/蓝图 = 一等公民）

本系统是 **API 驱动的声明式插件系统**：能力只在运行态经 API 暴露与消费；蓝图与 API 是一等公民，**禁止蓝图重名、禁止重复造可能与已有 API 重叠的插件代码**（避免能力分叉，省磁盘与维护）。

**开发外部插件的第一优先级：先查系统有没有现成 API 可用——**
- 运行态：`GET /` + `GET /Documentation/get_blueprints` + `POST /Documentation/get_blueprint_routes`（蓝图=插件、函数=工具）
- 开发态：本仓库（官方插件）与 [AssistantSay-VerificationLibrary](https://github.com/NSQTY/AssistantSay-VerificationLibrary)（校验库）的 README

**复用（两种形态都允许）**：
1. **透传**：调用现成 API，原封不动返回其 `result`；
2. **封装**：调用现成 API（作为底层），在其 `result` 之上二次解析/加工。

**调用通道（文档约定）**：插件路由函数内调用系统内现成 API 用 `requests.post`，基址取 `request.host_url`（不写死地址）：
```python
import requests, System

def call_api(path: str, payload: dict):
    base = System.flask.request.host_url.rstrip('/')
    r = requests.post(base + path, json=payload, timeout=10)
    r.raise_for_status()
    return r.json()                    # 统一信封 {"result": ...} / {"error": ...}
```
然后：
```python
data = call_api('/Workspace/WorksList', {})
return data['result']                  # ① 透传 result
# 或 result 二次加工: parsed = [w for w in data['result'] if w.get('enabled')]
```

**禁止**：从零重写系统已有的底层能力（会与已有 API 重叠、分叉能力）。

**重叠的机械保证**：蓝图重名只可能来自外部插件（官方内部受控）——**Workspace 登记时预注册检测**：模块未创建任何新蓝图（名已被官方/其他工作空间占用）即拒绝登记。

---

## Clone 官方插件的注意事项

1. **唯一获取源**：本仓库是官方唯一来源，避免多源分叉、版本混乱
2. **README.md 是结构契约强制要求**：没有 README.md 的插件不符合规范
3. **不要修改包结构**：名字合一、一层包是骨架依赖的基础
4. **不要修改内部依赖取用方式**：必须 `import System`，禁止直接 import flask
5. **登记 + 重载缺一不可**：只复制不登记不生效，只登记不重载不生效
6. **蓝图缓存**：改了蓝图配置后必须重载才能生效（同名字第二次访问不会覆盖）
7. **加载时机**：插件文件不能在 System 完整初始化前被 import，否则会 AttributeError
8. **禁止改代码**：只能改 `__init__.py` 的登记行，禁止修改插件内部代码或创建新文件

---

## 红线
- 禁止修改 SERVE 下任何 .py 文件
- 禁止在 SERVE 内部创建新文件
- 禁止删除 SERVE 下的 `FunctionTools/`、`VerificationLibrary/`、`System/` 三个文件夹
- 禁止绕过 `@CheckRequester()` 闸门直接注册路由
- 禁止在蓝图文件中使用深路径 import
