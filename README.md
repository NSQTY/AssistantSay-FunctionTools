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
- `return` 注解被跳过，不参与契约
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

## 装配到 SERVE 的流程

### 方式 1：clone
```bash
cd your_path/AssistantSay-SERVE/FunctionTools
git clone <本仓库地址>/<插件名>
```

### 方式 2：复制
```bash
cp -r your_path/AssistantSay-FunctionTools/<插件名> your_path/AssistantSay-SERVE/FunctionTools/
```

### 装配后必须两步
1. **登记**：在 `SERVE/FunctionTools/__init__.py` 加一行（**唯一允许改动的文件**）
   ```python
   from .<插件名> import <插件名>
   ```
2. **重载**：`POST /overload?reason=登记了新插件<插件名>`

> ⚠️ 禁止修改 `__init__.py` 以外的任何文件，禁止在 SERVE 内部创建新文件。

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
