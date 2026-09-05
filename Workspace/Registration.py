"""工作空间注册插件(Workspace): 登记第三方工作空间 + 必备文件校验 + 生命周期管理

开发范式:
    import System(唯一门面) / 蓝图即属性(CBP.Workspace) / 名字合一 / Annotated 契约 / 套闸门

第三方插件结构契约(登记时必须配齐):
    README.md  —— 必备(功能/API/参数/边界)
"""

from pathlib import Path
import json
import importlib.util
from typing import Annotated
import System

AR = System.FlaskApp.AR
CheckRequester = System.RouteInterception.CheckRequester

# 工作注册表(联动文件): 持久化已登记的外化工作空间
WORKS_FILE = Path(__file__).parent / 'Works.json'

# 第三方插件必备依赖文件(结构契约)
REQUIRED_FILES = ('README.md',)


def LoadWorks() -> list:
    """读取工作注册表(Works.json)"""
    try:
        works = json.loads(WORKS_FILE.read_text(encoding='utf-8'))
        return works if isinstance(works, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def SaveWorks(works: list):
    """写回工作注册表(Works.json)"""
    WORKS_FILE.write_text(json.dumps(works, ensure_ascii=False, indent=2), encoding='utf-8')


def FindEntry(works: list, WorksPath: str):
    """按 工作空间路径 查找注册项"""
    for entry in works:
        if entry.get('WorksPath') == WorksPath:
            return entry
    return None


def CheckRequiredFiles(WorksPath: str):
    """校验第三方插件必备文件(README.md 必写)——不齐则拒绝登记"""
    p = Path(WorksPath)
    if not p.exists():
        raise FileNotFoundError(f'工作空间不存在: {WorksPath}')
    missing = [f for f in REQUIRED_FILES if not (p / f).exists()]
    if missing:
        raise FileNotFoundError(f'工作空间缺少必备文件(结构契约): {missing} — 请先配齐 README.md 等')


def LoadBlueprintModule(WorksPath: str, Module: str):
    """从工作空间加载蓝图模块: 模块级 CBP.xxx 会自动把蓝图挂到 AR 上"""
    file_path = Path(WorksPath) / Module
    if not file_path.exists():
        raise FileNotFoundError(f'蓝图模块不存在: {file_path}')
    module_name = Path(Module).stem
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _blueprint_names() -> set:
    """当前应用实例上已挂载的蓝图名(属性即蓝图: CBP.xxx 挂到 AR 上)"""
    return {name for name, obj in vars(System.FlaskApp.AR).items()
            if isinstance(obj, System.Blueprint)}


def LoadAllWorks():
    """启动时: 加载已启用且必备文件齐全的工作空间蓝图模块, 并把条目创建的蓝图名回填注册表

    Flask 应用在第一次请求后冻结, 运行期不能注册新蓝图,
    所以外化蓝图必须在此阶段(启动时)加载; 请求只负责登记/状态/移除。
    蓝图名回填: 加载前后对比 AR 上蓝图集合, 差值 = 本条目创建的蓝图 → 写回条目(blueprint_names),
    供消费端(如 webui)把蓝图关联回工作空间条目(区分官方/外部)。
    """
    works = LoadWorks()
    changed = False
    for entry in works:
        if not entry.get('enabled', True):
            continue                          # 关闭状态的插件跳过
        try:
            CheckRequiredFiles(entry['WorksPath'])
            before = _blueprint_names()
            LoadBlueprintModule(entry['WorksPath'], entry['Module'])
            created = sorted(_blueprint_names() - before)
            if created and set(entry.get('blueprint_names', [])) != set(created):
                entry['blueprint_names'] = created
                changed = True
        except (FileNotFoundError, KeyError):
            continue
    if changed:
        SaveWorks(works)


# 名字合一: 蓝图名(包名 Workspace) == url_prefix
Workspace = AR.CBP.Workspace.ModifyConfiguration(url_prefix='/Workspace')

# 启动即加载已登记且启用的工作空间(在 RegisterBlueprints 之前)
LoadAllWorks()


@Workspace.route('/RegistrationWorks', methods=['POST', 'GET'])
@CheckRequester()
def RegistrationWorks(WorksPath: Annotated[str, '第三方插件工作空间目录(须配齐 README.md)'], Module: Annotated[str, '蓝图模块文件名(包内, 如 Workspace.py)']) -> Annotated[dict, '登记结果: 模块导入测试通过后写入注册表, 重载后生效']:
    '''登记第三方工作空间: importlib 导入测试——无报错才写入注册表; 有报错 try 捕获返回给请求者'''
    CheckRequiredFiles(WorksPath)                    # ① 必备文件(README.md)
    try:
        LoadBlueprintModule(WorksPath, Module)       # ② 预注册: 现在就导入测试模块(有错即拒, 不留死条目)
    except Exception as e:
        raise ValueError(f'预注册失败(模块导入测试): {type(e).__name__}: {e}') from e

    works = LoadWorks()
    entry = {'WorksPath': WorksPath, 'Module': Module, 'enabled': True}
    if FindEntry(works, WorksPath) is None:
        works.append(entry)
        SaveWorks(works)
    return {'registered': entry, 'works_total': len(works), 'effect': '预注册通过, 重载后生效'}


@Workspace.route('/WorksStatus', methods=['POST', 'GET'])
@CheckRequester()
def WorksStatus(WorksPath: Annotated[str, '第三方插件工作空间目录'], Enabled: Annotated[bool, '启用(True)或关闭(False)']) -> Annotated[dict, '状态更新结果, 重载后生效']:
    '''启用/关闭工作空间: 修改注册表中的 enabled 状态'''
    if isinstance(Enabled, str):
        raise ValueError(f'Enabled 必须是布尔值 true/false, 收到: {Enabled!r}')
    works = LoadWorks()
    entry = FindEntry(works, WorksPath)
    if entry is None:
        raise ValueError(f'未登记: {WorksPath}')
    entry['enabled'] = bool(Enabled)
    SaveWorks(works)
    return {'updated': entry, 'effect': '重载后生效'}


@Workspace.route('/RemoveWorks', methods=['POST', 'GET'])
@CheckRequester()
def RemoveWorks(WorksPath: Annotated[str, '第三方插件工作空间目录']) -> Annotated[dict, '移除结果: 已从注册表删除, 重载后不再加载']:
    '''移除工作空间: 从注册表删除'''
    works = LoadWorks()
    entry = FindEntry(works, WorksPath)
    if entry is None:
        raise ValueError(f'未登记: {WorksPath}')
    works.remove(entry)
    SaveWorks(works)
    return {'removed': entry, 'works_total': len(works)}


@Workspace.route('/WorksList', methods=['POST', 'GET'])
@CheckRequester()
def WorksList() -> Annotated[list, '当前注册表全部工作空间及状态']:
    '''查看注册表: 所有工作空间的 路径/模块/启用状态'''
    return LoadWorks()
