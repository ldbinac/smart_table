"""
记录评论与 @提及 功能测试
覆盖 TC-COMMENT-001 ~ TC-COMMENT-012
"""
import pytest

from app.models.user import User
from app.models.base import BaseMember, MemberRole
from app.extensions import db
from app.models.table_share import (
    TableShare,
    TableShareMember,
    TableSharePermission,
)
from app.models.notification import Notification
from app.models.record import Record, RecordComment
from app.models.comment import CommentMention, RecordFollower


def _login(client, email, password='Test1234!'):
    resp = client.post('/api/auth/login', json={
        'email': email, 'password': password, 'captcha': 'TEST'
    })
    if resp.status_code == 200:
        data = resp.get_json()
        token = data.get('data', {}).get('tokens', {}).get('access_token') \
            or data.get('data', {}).get('access_token')
        if token:
            return {'Authorization': f'Bearer {token}'}
    return {}


@pytest.fixture
def commenter_user(app, db_session):
    u = User(email='commenter@example.com', name='评论者')
    u.set_password('Test1234!')
    db.session.add(u)
    db.session.commit()
    db.session.refresh(u)
    return u


@pytest.fixture
def zhangsan_user(app, db_session):
    u = User(email='zhangsan@example.com', name='张三')
    u.set_password('Test1234!')
    db.session.add(u)
    db.session.commit()
    db.session.refresh(u)
    return u


@pytest.fixture
def commenter_auth_headers(client, commenter_user):
    return _login(client, 'commenter@example.com')


@pytest.fixture
def zhangsan_auth_headers(client, zhangsan_user):
    return _login(client, 'zhangsan@example.com')


@pytest.fixture
def seed_members(db_session, test_base, test_editor_user, test_viewer_user,
                 commenter_user, zhangsan_user):
    """将 editor/viewer/commenter/张三 加入 Base，作为可访问成员"""
    for u, role in [
        (test_editor_user, MemberRole.EDITOR),
        (test_viewer_user, MemberRole.VIEWER),
        (commenter_user, MemberRole.COMMENTER),
        (zhangsan_user, MemberRole.COMMENTER),
    ]:
        db.session.add(BaseMember(base_id=test_base.id, user_id=u.id, role=role))
    db.session.commit()


def _post_comment(client, headers, record_id, content, parent_id=None):
    return client.post(
        f'/api/records/{record_id}/comments',
        headers=headers,
        json={'content': content, 'parent_id': parent_id}
    )


# ---------------------------------------------------------------------------
# TC-COMMENT-001 评论列表查看（Viewer 可读）
# ---------------------------------------------------------------------------
def test_list_comments_viewer_can_read(client, auth_headers, viewer_auth_headers,
                                       test_record, seed_members):
    # 初始为空
    resp = client.get(f'/api/records/{test_record.id}/comments', headers=viewer_auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()['meta']['pagination']['total'] == 0

    # 所有者发表评论
    r = _post_comment(client, auth_headers, test_record.id, '第一条评论')
    assert r.status_code == 201

    # Viewer 可读取
    resp = client.get(f'/api/records/{test_record.id}/comments', headers=viewer_auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()['data']
    assert resp.get_json()['meta']['pagination']['total'] == 1
    assert data[0]['content'] == '第一条评论'


# ---------------------------------------------------------------------------
# TC-COMMENT-002 发表评论（Commenter+）
# ---------------------------------------------------------------------------
def test_create_comment_commenter(client, commenter_auth_headers, test_record, seed_members):
    r = _post_comment(client, commenter_auth_headers, test_record.id, '评论者说点什么')
    assert r.status_code == 201
    assert r.get_json()['data']['content'] == '评论者说点什么'


# ---------------------------------------------------------------------------
# TC-COMMENT-003 回复评论
# ---------------------------------------------------------------------------
def test_reply_comment(client, auth_headers, test_record, seed_members):
    top = _post_comment(client, auth_headers, test_record.id, '顶层评论')
    top_id = top.get_json()['data']['id']
    reply = _post_comment(client, auth_headers, test_record.id, '回复你', parent_id=top_id)
    assert reply.status_code == 201
    assert reply.get_json()['data']['parent_id'] == top_id

    resp = client.get(f'/api/records/{test_record.id}/comments', headers=auth_headers)
    items = resp.get_json()['data']
    assert len(items) == 1
    assert items[0]['replies'][0]['content'] == '回复你'


# ---------------------------------------------------------------------------
# TC-COMMENT-004 编辑 / 删除自己的评论（无回复则硬删）
# ---------------------------------------------------------------------------
def test_edit_and_delete_own_comment(client, commenter_auth_headers, test_record, seed_members):
    r = _post_comment(client, commenter_auth_headers, test_record.id, '原始内容')
    cid = r.get_json()['data']['id']

    # 编辑
    e = client.put(f'/api/comments/{cid}', headers=commenter_auth_headers,
                   json={'content': '已编辑'})
    assert e.status_code == 200
    assert e.get_json()['data']['content'] == '已编辑'

    # 删除（无回复 -> 硬删）
    d = client.delete(f'/api/comments/{cid}', headers=commenter_auth_headers)
    assert d.status_code == 200
    resp = client.get(f'/api/records/{test_record.id}/comments', headers=commenter_auth_headers)
    assert resp.get_json()['meta']['pagination']['total'] == 0


# ---------------------------------------------------------------------------
# TC-COMMENT-005 Editor+ 删除任意评论；Viewer 不可
# ---------------------------------------------------------------------------
def test_editor_delete_any_comment(client, auth_headers, editor_auth_headers,
                                   viewer_auth_headers, test_record, seed_members):
    r = _post_comment(client, auth_headers, test_record.id, '待删除')
    cid = r.get_json()['data']['id']

    # Viewer 删除 -> 403
    dv = client.delete(f'/api/comments/{cid}', headers=viewer_auth_headers)
    assert dv.status_code == 403

    # Editor 删除 -> 200
    de = client.delete(f'/api/comments/{cid}', headers=editor_auth_headers)
    assert de.status_code == 200


# ---------------------------------------------------------------------------
# TC-COMMENT-006 @提及解析与通知
# ---------------------------------------------------------------------------
def test_mention_notification(client, auth_headers, zhangsan_user, test_record, seed_members):
    r = _post_comment(client, auth_headers, test_record.id, '请 @张三 看一下')
    assert r.status_code == 201

    # comment_mentions 写入
    cid = r.get_json()['data']['id']
    mentions = CommentMention.query.filter_by(comment_id=cid).all()
    assert any(str(m.mentioned_user_id) == str(zhangsan_user.id) for m in mentions)

    # 张三收到 @提及通知
    n = Notification.query.filter_by(
        recipient_user_id=zhangsan_user.id, template_key='comment_mention'
    ).count()
    assert n >= 1


# ---------------------------------------------------------------------------
# TC-COMMENT-007 回复通知
# ---------------------------------------------------------------------------
def test_reply_notification(client, auth_headers, zhangsan_auth_headers,
                             test_user, test_record, seed_members):
    top = _post_comment(client, auth_headers, test_record.id, 'owner 的评论')
    top_id = top.get_json()['data']['id']

    # 张三回复 owner
    reply = _post_comment(client, zhangsan_auth_headers, test_record.id, '张三回复', parent_id=top_id)
    assert reply.status_code == 201

    # owner 收到回复通知
    n = Notification.query.filter_by(
        recipient_user_id=test_user.id, template_key='comment_reply'
    ).count()
    assert n >= 1


# ---------------------------------------------------------------------------
# TC-COMMENT-008 记录评论通知（关注者）
# ---------------------------------------------------------------------------
def test_record_comment_notification(client, auth_headers, zhangsan_auth_headers,
                                      zhangsan_user, test_record, seed_members):
    # 张三关注记录
    f = client.post(f'/api/records/{test_record.id}/follow', headers=zhangsan_auth_headers)
    assert f.status_code == 200
    assert f.get_json()['data']['following'] is True

    # owner 发表顶层评论
    r = _post_comment(client, auth_headers, test_record.id, '新评论给关注者')
    assert r.status_code == 201

    # 张三收到记录评论通知
    n = Notification.query.filter_by(
        recipient_user_id=zhangsan_user.id, template_key='record_comment'
    ).count()
    assert n >= 1


# ---------------------------------------------------------------------------
# TC-COMMENT-009 权限边界：Viewer 不能评论
# ---------------------------------------------------------------------------
def test_viewer_cannot_comment(client, viewer_auth_headers, test_record, seed_members):
    r = _post_comment(client, viewer_auth_headers, test_record.id, '我不应能评论')
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# TC-COMMENT-010 @提及范围：仅可访问成员
# ---------------------------------------------------------------------------
def test_mention_scope_only_accessible(client, auth_headers, test_record, seed_members):
    # 提及一个非 Base 成员名称，不应产生 mention 记录/通知
    r = _post_comment(client, auth_headers, test_record.id, '你好 @外部人员')
    assert r.status_code == 201
    cid = r.get_json()['data']['id']
    assert CommentMention.query.filter_by(comment_id=cid).count() == 0


# ---------------------------------------------------------------------------
# TC-COMMENT-011 边界：空内容 / 超长 / XSS 存储 / 级联删除
# ---------------------------------------------------------------------------
def test_comment_boundaries(client, auth_headers, test_record, seed_members, app, db_session):
    # 空内容
    empty = _post_comment(client, auth_headers, test_record.id, '   ')
    assert empty.status_code == 400

    # 超长
    long = _post_comment(client, auth_headers, test_record.id, 'x' * 2001)
    assert long.status_code == 400

    # XSS 内容原样存储（前端渲染时转义）
    xss = _post_comment(client, auth_headers, test_record.id, '<script>alert(1)</script> 文本')
    assert xss.status_code == 201
    assert '<script>' in xss.get_json()['data']['content']

    # 记录删除级联清理评论
    cid = xss.get_json()['data']['id']
    rec = Record.query.get(test_record.id)
    db.session.delete(rec)
    db.session.commit()
    assert RecordComment.query.filter_by(id=cid).count() == 0


# ---------------------------------------------------------------------------
# TC-COMMENT-012 通知偏好
# ---------------------------------------------------------------------------
def test_notification_preference_off(client, auth_headers, zhangsan_auth_headers,
                                     zhangsan_user, test_record, seed_members):
    # 默认偏好
    g = client.get('/api/users/me/notification-prefs', headers=zhangsan_auth_headers)
    assert g.status_code == 200
    assert g.get_json()['data']['notify_on_mention'] is True

    # 关闭 @提及通知
    p = client.put('/api/users/me/notification-prefs', headers=zhangsan_auth_headers,
                   json={'notify_on_mention': False})
    assert p.status_code == 200
    assert p.get_json()['data']['notify_on_mention'] is False

    # owner 提及张三 -> 不应收到 @提及通知
    before = Notification.query.filter_by(
        recipient_user_id=zhangsan_user.id, template_key='comment_mention'
    ).count()
    _post_comment(client, auth_headers, test_record.id, '再 @张三 一次')
    after = Notification.query.filter_by(
        recipient_user_id=zhangsan_user.id, template_key='comment_mention'
    ).count()
    assert after == before


# ---------------------------------------------------------------------------
# TC-COMMENT-013 表分享 editor 可删除任意评论（删除权限矩阵校验）
# ---------------------------------------------------------------------------
def test_share_editor_can_delete_any_comment(
    client, auth_headers, test_table, test_record, db_session
):
    # 通过表分享加入的 editor 用户
    sharer = User(email='sharer@example.com', name='分享编辑者')
    sharer.set_password('Test1234!')
    db.session.add(sharer)
    db.session.commit()
    db.session.refresh(sharer)

    share = TableShare(
        table_id=test_table.id,
        share_token='tok-editor-delete',
        created_by=sharer.id,
        permission=TableSharePermission.EDITOR,
        is_active=True,
    )
    db.session.add(share)
    db.session.flush()
    db.session.add(TableShareMember(share_id=share.id, user_id=sharer.id))
    db.session.commit()

    sharer_headers = _login(client, 'sharer@example.com')

    # owner 发表评论
    r = _post_comment(client, auth_headers, test_record.id, 'owner 的评论')
    cid = r.get_json()['data']['id']

    # 表分享 editor 删除他人评论 -> 200
    d = client.delete(f'/api/comments/{cid}', headers=sharer_headers)
    assert d.status_code == 200


# ---------------------------------------------------------------------------
# TC-COMMENT-014 关注者同时被 @提及：应同时收到提及通知与记录评论通知
# ---------------------------------------------------------------------------
def test_mention_and_follow_both_notified(
    client, auth_headers, zhangsan_auth_headers, zhangsan_user, test_record, seed_members
):
    # 张三关注记录
    client.post(f'/api/records/{test_record.id}/follow', headers=zhangsan_auth_headers)

    # owner 顶层评论并 @张三
    r = _post_comment(client, auth_headers, test_record.id, '@张三 请看这条关注记录')
    assert r.status_code == 201

    mention_n = Notification.query.filter_by(
        recipient_user_id=zhangsan_user.id, template_key='comment_mention'
    ).count()
    record_n = Notification.query.filter_by(
        recipient_user_id=zhangsan_user.id, template_key='record_comment'
    ).count()
    assert mention_n >= 1
    assert record_n >= 1


