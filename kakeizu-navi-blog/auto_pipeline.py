# -*- coding: utf-8 -*-
# 全自動: キューから1テーマ消化 → 生成 → 公開 → 広告挿入。ログは auto_log.txt。
import subprocess, sys, os, datetime
BASE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
LOG = os.path.join(BASE, "auto_log.txt")
QUEUE = os.path.join(BASE, "topics_queue.txt")

def run(args):
    env = dict(os.environ); env["PYTHONUTF8"] = "1"
    env.setdefault("GEMINI_MODEL", "gemini-2.5-flash-lite")
    try:
        r = subprocess.run([PY] + args, cwd=BASE, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=300, env=env)
        return (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return "[%s 実行エラー] %s\n" % (args[0], e)

def pop_topic():
    """キュー先頭の有効テーマを1つ取り出し、その行を削除。無ければ None。"""
    if not os.path.exists(QUEUE):
        return None
    lines = open(QUEUE, encoding="utf-8").read().splitlines()
    for i, ln in enumerate(lines):
        t = ln.strip()
        if t and not t.startswith("#"):
            topic = t
            del lines[i]
            open(QUEUE, "w", encoding="utf-8").write("\n".join(lines) + "\n")
            return topic
    return None

def main():
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write("\n===================== %s (auto_pipeline) =====================\n" % ts)
        topic = pop_topic()
        if topic:
            f.write("[1/3 生成] テーマ: %s\n" % topic)
            tmp = os.path.join(BASE, "_next_topic.txt")
            open(tmp, "w", encoding="utf-8").write(topic + "\n")
            f.write(run(["generate_articles.py", "--topics", "_next_topic.txt", "--max-total", "120"]))
            try: os.remove(tmp)
            except Exception: pass
        else:
            f.write("[1/3 生成] キュー空→AI自動提案\n")
            f.write(run(["generate_articles.py", "--auto", "1", "--max-total", "120"]))
        f.write("[2/3 公開]\n" + run(["post_to_livedoor.py", "--publish"]))
        f.write("[3/3 広告]\n" + run(["inject_affiliate.py", "--last", "3"]))
        f.write("[完了]\n")

if __name__ == "__main__":
    main()
