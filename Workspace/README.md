# Workspace（工作空间注册插件）

## 能力定位
**首个官方插件**（官方插件范式的示范），也是**第三方注册的唯一通道**——SERVE 对第三方只此一条外部化通道：clone 项目后必须先经官方装配动作安装本插件，否则第三方无法注册任何插件。为解决插件开发中"复制/clone 插件文件夹 + 改 `__init__.py` 登记行"的频繁手工流程而生：有了它，外部化插件注册只需走 API——登记插件目录 → README 必备校验 + **模块导入测试（预注册）** → 通过才写入注册表 → 重载后由系统启动时自动装配，**无需改动 SERVE 骨架任何一个字节**。

## 功能
登记第三方插件工作空间：把外化开发的插件（含 README.md 的独立目录）登记进注册表 `Works.json`，重载后由系统在**启动时**（LoadAllWorks）加载其蓝图模块。启动后请求只负责登记/状态/移除——Flask 在第一次请求后冻结，运行期不能注册新蓝图。

## 装配方式
官方插件（属于 AssistantSay-FunctionTools 仓库）——**官方装配动作**（消费者执行官方安装步骤时允许；第三方不得自行 copy/改 init）。按仓库根 README 流程：把本文件夹 clone/copy 进 `SERVE/FunctionTools/`，在 `SERVE/FunctionTools/__init__.py` 登记一行：

```python
from .Workspace import Registration
```

然后 `POST /overload?reason=登记了Workspace插件`。

## API（统一信封：成功 `{"result": ...}`，失败 `{"error": ...}`）

| 方法 | 路径 | 参数 | 说明 |
|---|---|---|---|
| POST/GET | `/Workspace/RegistrationWorks` | `WorksPath: str` 第三方插件目录<br>`Module: str` 蓝图模块文件名（目录内，如 `Workspace.py`） | 登记：README 必备 + **模块导入测试（预注册，try 捕获，有错即拒，不留死条目）** → 通过才写注册表。返回 `{registered, works_total, effect: 预注册通过, 重载后生效}` |
| POST/GET | `/Workspace/WorksStatus` | `WorksPath: str`<br>`Enabled: bool`（必须布尔） | 启用/关闭。未登记或类型错 → 抛错 |
| POST/GET | `/Workspace/RemoveWorks` | `WorksPath: str` | 移除登记。未登记 → 抛错 |
| POST/GET | `/Workspace/WorksList` | — | 查看注册表全部条目（路径/模块/启用状态） |

## 结构契约（登记第三方工作空间时的强制校验）
- **必备文件：README.md**（功能/API/参数/边界）——不齐拒绝登记
- 蓝图模块：目录内一个 Python 模块，模块级 `AR.CBP.<名>.ModifyConfiguration(...)` 建蓝图（蓝图即属性，名字合一）
- 第三方插件其余结构自由

## 边界与红线
- 本插件只登记与改状态；蓝图真实加载发生在启动时，**所有改动重载后生效**
- 注册表文件 `Works.json` 为运行时生成数据，不入库
- 插件开发范式与红线见 AssistantSay-FunctionTools 仓库根 README

## 依赖声明
- 校验库版本：基座（仅默认 FunctionHandler，无分支依赖）
