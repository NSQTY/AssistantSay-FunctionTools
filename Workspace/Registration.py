"""工作空间注册插件(Workspace): 登记第三方插件包 + 包契约校验 + 生命周期管理

开发范式:
    import System(唯一门面) / 蓝图即属性(CBP.Workspace) / 名字合一 / Annotated 契约 / 套闸门

第三方插件包结构契约(登记时必须配齐, 校验轻量):
    README.md         —— 必备(功能/API/参数/边界)
    requirements.txt  —— 必备(声明 Python 第三方依赖, 无依赖可为空行; 不自动安装, 由装配方按需 pip install)
    __init__.py       —— 包身份证(可为空注释): 目录即 Python 包, main.py 才能相对导入子模块
    main.py           —— 蓝图入口(固定名, 模块级 CBP.xxx 建蓝图)
    其余任意          —— 子模块/子包/资源/数据(被 main.py 相对导入即可, Workspace 不关心)
"""

from pathlib import Path
import json
import os
import re
import sys
import importlib.util
from typing import Annotated
import System

AR = System.FlaskApp.AR
CheckRequester = System.RouteInterception.CheckRequester

# 工作注册表(联动文件): 持久化已登记的外化工作空间
WORKS_FILE = Path(__file__).parent / 'Works.json'

# 第三方插件必备依赖文件(结构契约——README 与 requirements.txt 必写; __init__/main 由包式加载器校验)
REQUIRED_FILES = ('README.md', 'requirements.txt')

# 固定蓝图入口文件名
ENTRY_FILE = 'main.py'


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
    """校验必备文件(README.md 必写)——不齐则拒绝登记"""
    p = Path(WorksPath)
    if not p.exists():
        raise FileNotFoundError(f'插件包不存在: {WorksPath}')
    missing = [f for f in REQUIRED_FILES if not (p / f).exists()]
    if missing:
        raise FileNotFoundError(f'插件包缺少必备文件(结构契约): {missing} — 请先配齐 README.md')


def _blueprint_names() -> set:
    """当前应用实例上已挂载的蓝图名(属性即蓝图: CBP.xxx 挂到 AR 上)"""
    return {name for name, obj in vars(System.FlaskApp.AR).items()
            if isinstance(obj, System.Blueprint)}


def LoadPluginPackage(WorksPath: str, legacy_module: str = None):
    """包式加载第三方插件: 目录 = Python 包(__init__.py 身份证), main.py = 蓝图入口(固定名)

    包先注册进 sys.modules(获得 __path__) → 入口模块按 包名.入口名 加载,
    main.py 内相对导入子模块/子包(`from .helpers import x`)天然可用, 无需 sys.path。
    legacy_module: 旧登记条目兼容(无 main.py 且带 Module 字段时, 按包内该模块加载)
    """
    dir_path = Path(WorksPath)
    pkg_name = dir_path.name
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', pkg_name):
        raise ValueError(f'插件目录名必须是合法 Python 标识符(目录名=包名): {pkg_name!r}')

    init_file = dir_path / '__init__.py'
    if not init_file.exists():
        raise FileNotFoundError(f'插件包缺少 __init__.py(包身份证, 可为空): {init_file}')

    entry_file = dir_path / ENTRY_FILE
    if not entry_file.exists():
        if legacy_module:
            entry_file = dir_path / legacy_module
        if not entry_file.exists():
            raise FileNotFoundError(f'插件包缺少蓝图入口 {ENTRY_FILE}(包契约): {entry_file}')

    # ① 注册包(身份证): sys.modules[包名] + __path__ 就位
    spec_pkg = importlib.util.spec_from_file_location(
        pkg_name, init_file, submodule_search_locations=[str(dir_path)])
    pkg = importlib.util.module_from_spec(spec_pkg)
    sys.modules[pkg_name] = pkg
    spec_pkg.loader.exec_module(pkg)

    # ② 加载蓝图入口为 包名.入口名(模块级 CBP.xxx 自动把蓝图挂到 AR 上)
    mod_name = f'{pkg_name}.{entry_file.stem}'
    spec = importlib.util.spec_from_file_location(mod_name, entry_file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def LoadAllWorks():
    """启动时: 加载已启用且结构契约齐全的第三方插件包, 并把蓝图名回填注册表

    Flask 应用在第一次请求后冻结, 运行期不能注册新蓝图,
    所以外化蓝图必须在此阶段(启动时)加载; 请求只负责登记/状态/移除。
    蓝图名回填: 加载前后对比 AR 上蓝图集合, 差值 = 本包创建的蓝图 → 写回条目(blueprint_names),
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
            LoadPluginPackage(entry['WorksPath'], legacy_module=entry.get('Module'))
            created = sorted(_blueprint_names() - before)
            if created and set(entry.get('blueprint_names', [])) != set(created):
                entry['blueprint_names'] = created
                changed = True
        except (FileNotFoundError, KeyError, ValueError):
            continue
    if changed:
        SaveWorks(works)


# 名字合一: 蓝图名(包名 Workspace) == url_prefix
Workspace = AR.CBP.Workspace.ModifyConfiguration(url_prefix='/Workspace')

# 启动即加载已登记且启用的工作空间(在 RegisterBlueprints 之前)
LoadAllWorks()


@Workspace.route('/RegistrationWorks', methods=['POST', 'GET'])
@CheckRequester()
def RegistrationWorks(WorksPath: Annotated[str, '第三方插件包目录(包契约: README.md + __init__.py + main.py)']) -> Annotated[dict, '登记结果: 包式预注册通过后写入注册表, 重载后生效']:
    '''登记第三方插件包: README 必备 + 包式预注册(main.py 蓝图入口, 有错即拒, 蓝图重名即拒)'''
    CheckRequiredFiles(WorksPath)                    # ① 必备文件(README.md)
    before = _blueprint_names()
    after = set()
    try:
        try:
            LoadPluginPackage(WorksPath)             # ② 预注册: 包式导入测试(蓝图入口固定 main.py)
        except Exception as e:
            raise ValueError(f'预注册失败(插件包导入测试): {type(e).__name__}: {e}') from e
        after = _blueprint_names()
    finally:
        # ③ 清理: 摘掉试加载挂上的蓝图(仅内存导入测试; 真实加载在重载后由 LoadAllWorks 做)
        for name in sorted(after - before):
            try:
                delattr(AR, name)
            except AttributeError:
                pass
    created = sorted(after - before)
    if not created:
        # ④ 禁止蓝图重叠: 未创建任何新蓝图 = 蓝图名被已有蓝图(官方/其他工作空间)占用(CBP 缓存吞掉)或 main.py 未建蓝图
        raise ValueError('预注册失败: main.py 未创建任何新蓝图——蓝图名可能与已存在蓝图重叠(官方或其他工作空间), 或未在入口建蓝图')

    works = LoadWorks()
    entry = FindEntry(works, WorksPath)
    if entry is None:
        entry = {'WorksPath': WorksPath, 'enabled': True, 'blueprint_names': []}
        works.append(entry)
    else:
        entry['enabled'] = True
        entry.pop('Module', None)                    # 新契约无 Module(入口固定 main.py)
    SaveWorks(works)
    return {'registered': entry, 'works_total': len(works), 'effect': '预注册通过, 重载后生效'}


@Workspace.route('/WorksStatus', methods=['POST', 'GET'])
@CheckRequester()
def WorksStatus(WorksPath: Annotated[str, '第三方插件包目录'], Enabled: Annotated[bool, '启用(True)或关闭(False)']) -> Annotated[dict, '状态更新结果, 重载后生效']:
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
def RemoveWorks(WorksPath: Annotated[str, '第三方插件包目录']) -> Annotated[dict, '移除结果: 已从注册表删除, 重载后不再加载']:
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
    '''查看注册表: 所有工作空间的 路径/蓝图/启用状态'''
    return LoadWorks()


# ---------- 服务器目录浏览(通用: 登记/任何 UI 挑选插件包目录用, 只列目录名不读内容) ----------

def _is_drive_root(path: str) -> bool:
    return len(path) >= 2 and path[1] == ':' and (len(path) == 2 or path[2] in '\\/')


def _list_drives() -> list:
    try:
        return sorted(os.listdrives())
    except AttributeError:
        return [f'{c}:\\' for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if Path(f'{c}:\\').exists()]


@Workspace.route('/browse', methods=['POST', 'GET'])
@CheckRequester()
def browse(path: Annotated[str, '要浏览的目录(留空=盘符列表)'] = None) -> Annotated[dict, '目录浏览结果: {path, parent, drives, dirs}']:
    """服务器目录浏览(通用 API): 列盘符/子目录名, 供登记/文件夹选择器挑选插件包目录(服务器可读的绝对路径)"""
    if not path:
        return {'path': '', 'parent': None, 'is_root': True, 'drives': _list_drives(), 'dirs': []}
    p = Path(path)
    if not p.is_absolute() or not p.exists() or not p.is_dir():
        raise ValueError(f'不是有效目录: {path}')
    dirs = sorted((d.name for d in p.iterdir() if d.is_dir()), key=str.lower)
    parent = None if _is_drive_root(str(p)) else str(p.parent)
    return {'path': str(p), 'parent': parent, 'is_root': False, 'drives': [], 'dirs': dirs}
