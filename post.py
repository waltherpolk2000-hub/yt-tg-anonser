"""
YouTube to Telegram autoposter.

Runs on GitHub Actions cron. Polls a YouTube channel's uploads playlist
RSS feed for new videos and posts to a Telegram channel via Bot API
with a randomized phrase (greeting + middle + CTA + URL).

State is kept in seen.json which is committed back to the repo by the
workflow after each run so subsequent runs don't repost old videos.
"""

import json
import os
import random
import sys

import feedparser
import requests

YT_PLAYLIST_ID = os.environ["YT_PLAYLIST_ID"]
TG_TOKEN = os.environ["TG_TOKEN"]
TG_CHAT_ID = os.environ["TG_CHAT_ID"]
STATE_FILE = "seen.json"

GREETINGS = [
    "Хей! 👋",
    "Минуточку внимания! 📣",
    "Ловите подгон! 🎁",
    "Срочные новости! 📢",
    "Бум! ⚡️",
    "Привет, народ! ✌️",
    "Тут такое дело... 👀",
    "Глянь, что у меня для тебя есть! 🤔",
]

MIDDLES = [
    "на канале только что вышел новый ролик.",
    "я наконец-то дропнул свежий видос.",
    "с пылу с жару прилетел новый видос.",
    "я закончил ковыряться в видеоредакторе и выкатил новый шедевр.",
    "ютуб обновился моим новым видеороликом.",
    "на канале материализовался свежий контент.",
    "новый выпуск уже прошел модерацию и ждет тебя.",
    "свежая порция пищи для ума (и глаз) уже на канале.",
    "я починил твое скучное расписание на этот час новым видео.",
]

CTAS = [
    "Бегом смотреть, пока горячее!",
    "Заваривай чаёк, усаживайся поудобнее и кликай по ссылке.",
    "Жду твой царский лайк и коммент под видео!",
    "Тыкай на ссылку и делись мнением в комментариях.",
    "Включай прямо сейчас, не откладывай на потом.",
    "Приятного просмотра!",
    "Не забудь прожать колокольчик и влепить лайк!",
    "Переходи по ссылке, пока алгоритмы не спрятали.",
    "Погнали смотреть, делитесь фидбеком!",
]


def load_state():
    if not os.path.exists(STATE_FILE):
        return {"seen": [], "initialized": False}
    with open(STATE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def fetch_feed():
    url = f"https://www.youtube.com/feeds/videos.xml?playlist_id={YT_PLAYLIST_ID}"
    feed = feedparser.parse(url)
    if feed.bozo:
        print(f"Warning: feed parse issue: {feed.bozo_exception}", file=sys.stderr)
    return feed


def build_message(video_url):
    phrase = (
        f"{random.choice(GREETINGS)} "
        f"{random.choice(MIDDLES)} "
        f"{random.choice(CTAS)}"
    )
    return f"{phrase}\n\n{video_url}"


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    r = requests.post(
        url,
        json={"chat_id": TG_CHAT_ID, "text": text},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def main():
    state = load_state()
    seen = set(state.get("seen", []))
    initialized = state.get("initialized", False)

    feed = fetch_feed()
    if not feed.entries:
        print("Feed is empty, nothing to do.")
        return

    entry_ids = [e.yt_videoid for e in feed.entries]

    if not initialized:
        state["seen"] = entry_ids
        state["initialized"] = True
        save_state(state)
        print(f"First run: marked {len(entry_ids)} existing videos as seen, no posting.")
        return

    new_entries = [e for e in feed.entries if e.yt_videoid not in seen]
    if not new_entries:
        print("No new videos.")
        return

    for entry in reversed(new_entries):
        vid_id = entry.yt_videoid
        video_url = f"https://www.youtube.com/watch?v={vid_id}"
        try:
            send_telegram(build_message(video_url))
            print(f"Posted: {vid_id} ({entry.title})")
            seen.add(vid_id)
        except Exception as exc:
            print(f"Failed to post {vid_id}: {exc}", file=sys.stderr)

    state["seen"] = list(seen)[-200:]
    save_state(state)


if __name__ == "__main__":
    main()
