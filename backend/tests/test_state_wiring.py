"""create_app 이 Player.on_state_change 를 SSE 허브에 연결하는지 검증.

auto-advance/사진진행 시 '지금 재생 중'이 즉시 방송되려면 이 연결이 필수.
"""
from app.web.main import create_app


def test_app_wires_player_state_change_to_hub():
    app = create_app(testing=True)
    player = app.state.deps.player
    assert player.on_state_change is not None

    # 콜백 실행 시 허브 publish 가 호출돼야(구독자에게 상태 전달)
    published = []
    app.state.hub.publish = lambda state: published.append(state)
    player.on_state_change()
    assert len(published) == 1
