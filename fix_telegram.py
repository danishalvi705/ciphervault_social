import re

with open("main.py", "r") as f:
    content = f.read()

old_send = r'''with open\(video_path, 'rb'\) as f:
        requests\.post\(
            f"https://api\.telegram\.org/bot\{token\}/sendVideo",
            files=\{"video": f\},
            data=\{"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"\}
        \)'''

new_send = '''try:
        with open(video_path, 'rb') as f:
            response = await asyncio.to_thread(
                requests.post,
                f"https://api.telegram.org/bot{token}/sendVideo",
                files={"video": f},
                data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
                timeout=30
            )
            logger.info(f"[TELEGRAM] Sent to {chat_id} | Status: {response.status_code}")
    except FileNotFoundError:
        logger.error(f"[TELEGRAM] Video not found: {video_path}")
    except Exception as e:
        logger.error(f"[TELEGRAM] Failed: {e}")'''

content = re.sub(old_send, new_send, content, flags=re.DOTALL)

with open("main.py", "w") as f:
    f.write(content)

print("[OK] Fixed send_telegram()")
