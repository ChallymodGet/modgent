import asyncio

from src.Agent import session_registry


class _Closable:
    def __init__(self, closed=False):
        self.closed = closed
        self.torn_down = False

    def is_closed(self):
        return self.closed

    async def close(self):
        self.torn_down = True

    async def stop(self):
        self.torn_down = True


def test_closed_window_is_dropped_so_apply_can_reopen():
    async def run():
        context = _Closable()
        await session_registry.register_session("closed-job", _Closable(), context, _Closable(closed=True))
        dropped = await session_registry.drop_if_closed("closed-job")
        return dropped, await session_registry.get_session("closed-job"), context.torn_down

    dropped, remaining, torn_down = asyncio.run(run())

    assert dropped
    assert remaining is None
    assert torn_down


def test_open_window_is_kept():
    async def run():
        await session_registry.register_session("open-job", _Closable(), _Closable(), _Closable(closed=False))
        dropped = await session_registry.drop_if_closed("open-job")
        remaining = await session_registry.get_session("open-job")
        await session_registry.close_session("open-job")
        return dropped, remaining

    dropped, remaining = asyncio.run(run())

    assert not dropped
    assert remaining is not None
