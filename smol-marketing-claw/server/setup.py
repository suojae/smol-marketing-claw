"""Interactive .env setup — prompt for missing API keys at server startup."""

import os

from dotenv import load_dotenv

# (group label, env var names)
_KEY_GROUPS = [
    (
        "X API",
        [
            "X_CONSUMER_KEY",
            "X_CONSUMER_SECRET",
            "X_ACCESS_TOKEN",
            "X_ACCESS_TOKEN_SECRET",
        ],
    ),
    (
        "Threads API",
        [
            "THREADS_USER_ID",
            "THREADS_ACCESS_TOKEN",
        ],
    ),
    (
        "LinkedIn API",
        [
            "LINKEDIN_ACCESS_TOKEN",
        ],
    ),
    (
        "Instagram API",
        [
            "INSTAGRAM_USER_ID",
            "INSTAGRAM_ACCESS_TOKEN",
        ],
    ),
    (
        "News (X Search)",
        [
            "NEWS_X_BEARER_TOKEN",
        ],
    ),
    (
        "Discord Bot Tokens",
        [
            "DISCORD_LEAD_TOKEN",
            "DISCORD_THREADS_TOKEN",
            "DISCORD_LINKEDIN_TOKEN",
            "DISCORD_INSTAGRAM_TOKEN",
            "DISCORD_NEWS_TOKEN",
        ],
    ),
    (
        "Discord Channel IDs",
        [
            "DISCORD_TEAM_CHANNEL_ID",
            "DISCORD_LEAD_CHANNEL_ID",
            "DISCORD_THREADS_CHANNEL_ID",
            "DISCORD_LINKEDIN_CHANNEL_ID",
            "DISCORD_INSTAGRAM_CHANNEL_ID",
            "DISCORD_NEWS_CHANNEL_ID",
        ],
    ),
]


def _read_existing_keys(env_path: str) -> set[str]:
    """Return set of key names already defined (non-empty) in the .env file."""
    defined: set[str] = set()
    if not os.path.exists(env_path):
        return defined
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("\"'")
                if value:
                    defined.add(key)
    return defined


def check_and_prompt_env(env_path: str) -> None:
    """Check for missing API keys and interactively prompt the user."""
    defined = _read_existing_keys(env_path)
    new_entries: list[str] = []

    for group_label, keys in _KEY_GROUPS:
        missing = [k for k in keys if k not in defined]
        if not missing:
            continue

        try:
            answer = input(
                f"{group_label} 키가 설정되지 않았습니다. 지금 입력하시겠습니까? (y/N): "
            )
        except (EOFError, KeyboardInterrupt):
            print()
            continue

        if answer.strip().lower() != "y":
            continue

        for key in missing:
            try:
                value = input(f"  {key}: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if value:
                new_entries.append(f"{key}={value}")

    if new_entries:
        with open(env_path, "a") as f:
            f.write("\n".join([""] + new_entries + [""]))
        print(f".env에 {len(new_entries)}개 키를 저장했습니다.")

    # Reload so os.environ reflects any new values
    load_dotenv(env_path, override=True)
