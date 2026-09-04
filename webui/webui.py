"""WEBui 官方插件: 系统看板 —— 插件/API 目录 + 收藏夹(嵌套组) + 调试

定位: 一个收束页(static/index.html)。看板数据全部由浏览器直接采集公开 API
      (Documentation / Workspace, 与 Agent 同一视角), 本插件不读 System 内部结构。
本插件只做三件事:
    1) 页面路由 /webui/home —— 渲染 static/index.html(页面语义, 类型响应自证)
    2) 收藏夹 CRUD —— /webui/*, 持久化到包内 webui.json(嵌套组: 组套组; 运行时数据不入库)
    3) API 信息 —— 用 V2 信息型校验器(蓝图信息/api信息/自定义信息 随 GET 自证)

开发范式: import System(唯一门面) / CBP 蓝图即属性 / 名字合一 / Annotated 契约 / 套闸门
"""
from pathlib import Path
import json
import uuid
from typing import Annotated
import System

AR = System.FlaskApp.AR
CheckRequester = System.RouteInterception.CheckRequester
# V2 信息型校验器(官方 VL 分支, 已挂载): 初始化传参声明 蓝图/api/自定义 信息, GET 自证
from VerificationLibrary.AssistantSay_HANDLER_V2 import Handler as InfoHandler

# 收藏夹数据文件(运行时数据, 插件包内, 不入库)
DATA_FILE = Path(__file__).resolve().parent / 'webui.json'


# ---------- 收藏夹持久化 ----------

def load_favorites() -> list:
    """读收藏夹组树; 无文件/损坏 → 空树"""
    try:
        data = json.loads(DATA_FILE.read_text(encoding='utf-8'))
        groups = data.get('groups', []) if isinstance(data, dict) else []
        return groups if isinstance(groups, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_favorites(groups: list):
    """写收藏夹组树"""
    DATA_FILE.write_text(json.dumps({'groups': groups}, ensure_ascii=False, indent=2), encoding='utf-8')


def find_group(groups: list, gid: str):
    """按 id 递归查组(返回组或 None)"""
    for g in groups:
        if g.get('id') == gid:
            return g
        hit = find_group(g.get('groups', []), gid)
        if hit is not None:
            return hit
    return None


def remove_group(groups: list, gid: str) -> bool:
    """按 id 递归删除组(含其子组与条目)"""
    for i, g in enumerate(groups):
        if g.get('id') == gid:
            groups.pop(i)
            return True
        if remove_group(g.get('groups', []), gid):
            return True
    return False


# ---------- 页面处理器(原型期就地子类; 稳定后升 VL 分支) ----------

class Page(System.VerificationLibrary.FunctionHandler):
    """看板页处理器: GET 渲染 static/index.html(浏览器端采集数据), 不执行函数"""

    def GET_dispatch(self, request, contract: dict, func):
        page = Path(__file__).resolve().parent / 'static' / 'index.html'
        if not page.exists():
            raise FileNotFoundError(f'看板页不存在: {page}')
        return page.read_text(encoding='utf-8')

    def GET_render(self, request, data):
        import System as _s
        return _s.flask.Response(data, content_type='text/html; charset=utf-8')


# 名字合一: 蓝图名(webui) == url_prefix(/webui); 蓝图级信息挂蓝图(普通属性, V2 自动回退读取)
WEBUI = AR.CBP.webui.ModifyConfiguration(
    url_prefix='/webui',
    蓝图信息={'能力': '系统看板', '来源': '官方插件', '说明': '插件/API 目录 + 契约 + 调试 + 收藏夹'},
)


@WEBUI.route('/home', methods=['GET'])
@CheckRequester(handler=Page())
def home():
    """看板页入口: 仅 GET(浏览器打开 /webui/home); POST 由闸门拒绝"""
    return ''


# ---------- 收藏夹 API(统一信封, 走闸门) ----------

@WEBUI.route('/favorites', methods=['POST', 'GET'])
@CheckRequester(handler=InfoHandler(
    api信息={'用途': '查看收藏夹整棵组树(嵌套组)', '调用': 'POST {} 或 GET 看契约+信息'},
    自定义信息={'分组': '收藏夹', '数据文件': 'webui.json'},
))
def favorites() -> Annotated[list, '收藏夹组树: [{id,name,groups:[...],items:[{bp,fn,url,is_page}]}]']:
    """查看收藏夹: POST {} 返回整棵组树"""
    return load_favorites()


@WEBUI.route('/group_add', methods=['POST', 'GET'])
@CheckRequester()
def group_add(name: Annotated[str, '组名(必填)'], parent_id: Annotated[str, '父组 id(可空=顶层)'] = None) -> Annotated[dict, '新增组结果']:
    """新增收藏组; parent_id 为空 → 顶层组"""
    name = (name or '').strip()
    if not name:
        raise ValueError('组名不能为空')
    groups = load_favorites()
    group = {'id': uuid.uuid4().hex[:8], 'name': name, 'groups': [], 'items': []}
    if parent_id:
        parent = find_group(groups, parent_id)
        if parent is None:
            raise ValueError(f'父组不存在: {parent_id}')
        parent['groups'].append(group)
    else:
        groups.append(group)
    save_favorites(groups)
    return {'added': group, 'groups_total': len(groups)}


@WEBUI.route('/group_rename', methods=['POST', 'GET'])
@CheckRequester()
def group_rename(id: Annotated[str, '组 id'], name: Annotated[str, '新组名']) -> Annotated[dict, '重命名结果']:
    """重命名组"""
    name = (name or '').strip()
    if not name:
        raise ValueError('组名不能为空')
    groups = load_favorites()
    g = find_group(groups, id)
    if g is None:
        raise ValueError(f'组不存在: {id}')
    g['name'] = name
    save_favorites(groups)
    return {'renamed': g}


@WEBUI.route('/group_remove', methods=['POST', 'GET'])
@CheckRequester()
def group_remove(id: Annotated[str, '组 id']) -> Annotated[dict, '删除结果(连子组与条目)']:
    """删除组(递归, 含子组与条目)"""
    groups = load_favorites()
    if not remove_group(groups, id):
        raise ValueError(f'组不存在: {id}')
    save_favorites(groups)
    return {'removed_id': id}


@WEBUI.route('/item_add', methods=['POST', 'GET'])
@CheckRequester()
def item_add(group_id: Annotated[str, '目标组 id'], bp: Annotated[str, '蓝图名'], fn: Annotated[str, '函数名'], url: Annotated[str, '直达链接(/蓝图名/函数名)'], is_page: Annotated[bool, '是否 HTML 页面'] = False) -> Annotated[dict, '收藏结果']:
    """往指定组添加收藏条目(只能从蓝图区发起)"""
    groups = load_favorites()
    g = find_group(groups, group_id)
    if g is None:
        raise ValueError(f'组不存在: {group_id}')
    if not url:
        raise ValueError('url 不能为空')
    for item in g['items']:
        if item.get('url') == url:
            raise ValueError(f'该条目已在组 {g["name"]} 中')
    item = {'bp': bp, 'fn': fn, 'url': url, 'is_page': bool(is_page)}
    g['items'].append(item)
    save_favorites(groups)
    return {'added': item, 'group': g['name']}


@WEBUI.route('/item_remove', methods=['POST', 'GET'])
@CheckRequester()
def item_remove(group_id: Annotated[str, '组 id'], url: Annotated[str, '条目 url']) -> Annotated[dict, '移除结果']:
    """从收藏组移除条目(只能在收藏区操作)"""
    groups = load_favorites()
    g = find_group(groups, group_id)
    if g is None:
        raise ValueError(f'组不存在: {group_id}')
    before = len(g['items'])
    g['items'] = [it for it in g['items'] if it.get('url') != url]
    if len(g['items']) == before:
        raise ValueError(f'条目不在该组: {url}')
    save_favorites(groups)
    return {'removed_url': url, 'group': g['name']}
