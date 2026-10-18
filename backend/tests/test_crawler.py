"""Tests for robots.txt and llms.txt detection."""

from crawler import blocked_ai_bots, looks_like_llms_txt


def test_blocked_ai_bots_reads_per_bot_rules() -> None:
    robots = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: CCBot\nDisallow: /\n\n" \
        "User-agent: *\nAllow: /\n"
    assert blocked_ai_bots(robots) == ["GPTBot", "CCBot"]


def test_wildcard_disallow_blocks_every_bot() -> None:
    assert "ClaudeBot" in blocked_ai_bots("User-agent: *\nDisallow: /\n")


def test_open_robots_blocks_nothing() -> None:
    assert blocked_ai_bots("User-agent: *\nDisallow: /admin\n") == []


def test_llms_txt_requires_h1() -> None:
    assert looks_like_llms_txt("# Acme\n\n> Invoicing API\n")
    assert not looks_like_llms_txt("")
    assert not looks_like_llms_txt("User-agent: *")

