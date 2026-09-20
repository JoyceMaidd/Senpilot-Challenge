import types

from uarb_agent.service import RateLimiter, should_ignore

ME = "regulatory_research@agentmail.to"


def msg(sender, headers=None):
    return types.SimpleNamespace(from_=sender, headers=headers or {})


def test_rate_limiter_window():
    rl = RateLimiter(2, window_s=100)
    assert rl.allow("a@x.com", now=0) and rl.allow("A@x.com", now=1)  # case-insensitive
    assert not rl.allow("a@x.com", now=2)
    assert rl.allow("b@x.com", now=2)  # per sender
    assert rl.allow("a@x.com", now=101)  # window slid


def test_ignores_own_and_automated_mail():
    assert should_ignore(msg(f"Agent <{ME}>"), ME)
    assert should_ignore(msg("MAILER-DAEMON@amazonses.com"), ME)
    assert should_ignore(msg("no-reply@service.com"), ME)
    assert should_ignore(msg("bot@x.com", {"Auto-Submitted": "auto-replied"}), ME)
    assert should_ignore(msg("bot@x.com", {"Precedence": "bulk"}), ME)
    assert should_ignore(msg(""), ME)


def test_accepts_normal_mail():
    assert should_ignore(msg("Jane Doe <jane@example.com>"), ME) is None
    assert should_ignore(msg("jane@example.com", {"Auto-Submitted": "no"}), ME) is None
